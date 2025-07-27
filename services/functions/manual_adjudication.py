import logging
from decimal import Decimal
from typing import Dict, List, Optional

from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.utils import timezone

from services.models import (
    Claim, AdjudicationResult, AdjudicationMessage,
    AdjudicationMessageCode, AdjudicationOverride
)

logger = logging.getLogger(__name__)

User = get_user_model()


class ManualAdjudicationEngine:
    """
    VitalSuite Manual Adjudication Engine

    Handles manual review and override of automated adjudication results.
    Provides adjudicators with tools to:
    - Review automated decisions
    - Override amounts and decisions
    - Add manual review notes
    - Apply discretionary adjustments
    - Track all manual interventions
    """

    def __init__(self, claim: Claim, adjudicator: User):
        self.claim = claim
        self.adjudicator = adjudicator
        self.original_result = self._get_latest_adjudication_result()
        self.override_messages = []

    def _get_latest_adjudication_result(self) -> Optional[AdjudicationResult]:
        """Get the latest adjudication result for this claim"""
        return self.claim.adjudication_results.filter(
            is_active=True
        ).order_by('-created_at').first()

    def review_claim(self, review_data: Dict) -> AdjudicationResult:
        """
        Manual review and potential override of automated adjudication

        Args:
            review_data: Dictionary containing review decision and parameters
            {
                'decision': 'approve'|'decline'|'modify'|'return_to_auto',
                'override_amount': Decimal (optional),
                'override_reason': str,
                'review_notes': str,
                'message_codes': List[str] (optional),
                'require_clinical_review': bool (optional),
                'payment_method': 'full'|'partial'|'withheld' (optional),
                'withholding_percentage': Decimal (optional),
                'additional_conditions': str (optional)
            }
        """

        logger.info(f"Manual review started for claim {self.claim.transaction_number} by {self.adjudicator.username}")

        try:
            with transaction.atomic():
                # Validate adjudicator permissions
                if not self._validate_adjudicator_permissions(review_data['decision']):
                    raise ValueError("Insufficient permissions for this action")

                # Process the manual decision
                if review_data['decision'] == 'approve':
                    return self._manual_approve(review_data)
                elif review_data['decision'] == 'decline':
                    return self._manual_decline(review_data)
                elif review_data['decision'] == 'modify':
                    return self._manual_modify(review_data)
                elif review_data['decision'] == 'return_to_auto':
                    return self._return_to_auto_adjudication(review_data)
                else:
                    raise ValueError(f"Invalid decision: {review_data['decision']}")

        except Exception as e:
            logger.error(f"Manual review error for claim {self.claim.transaction_number}: {str(e)}")
            raise

    def _validate_adjudicator_permissions(self, decision: str) -> bool:
        """Validate if adjudicator has permission for the requested action"""

        # Check basic adjudication permission
        if not self.adjudicator.has_perm('services.can_adjudicate_claims'):
            return False

        # Check high-value claim permissions
        if self.original_result and self.original_result.claimed_amount > Decimal('10000'):
            if not self.adjudicator.has_perm('services.can_adjudicate_high_value'):
                return False

        # Check clinical review permissions
        if decision == 'clinical_review':
            if not self.adjudicator.has_perm('services.can_clinical_review'):
                return False

        # Check override permissions for reversing auto-decisions
        if self.original_result and self.original_result.processing_type == 'AUTO':
            if not self.adjudicator.has_perm('services.can_override_auto_adjudication'):
                return False

        return True

    def _manual_approve(self, review_data: Dict) -> AdjudicationResult:
        """Manually approve a claim with optional modifications"""

        # Determine approval amounts
        if 'override_amount' in review_data and review_data['override_amount']:
            approved_amount = review_data['override_amount']
        elif self.original_result:
            approved_amount = self.original_result.accepted_amount
        else:
            approved_amount = self.claim.claimed_amount

        # Create override record
        override = self._create_override_record(
            new_decision='APPROVED',
            new_amount=approved_amount,
            override_reason=review_data['override_reason'],
            review_notes=review_data.get('review_notes', '')
        )

        # Create new adjudication result
        new_result = AdjudicationResult.objects.create(
            claim=self.claim,
            result='APPROVED',
            claimed_amount=self.claim.claimed_amount,
            accepted_amount=approved_amount,
            adjudicated_amount=approved_amount,
            processing_type='MANUAL',
            processed_by=self.adjudicator,
            processed_at=timezone.now(),
            override_record=override,
            review_notes=review_data.get('review_notes', ''),
            requires_clinical_review=review_data.get('require_clinical_review', False)
        )

        # Handle payment method specifications
        payment_method = review_data.get('payment_method', 'full')
        if payment_method == 'partial':
            new_result.partial_payment = True
        elif payment_method == 'withheld':
            withholding_pct = review_data.get('withholding_percentage', 0)
            if withholding_pct > 0:
                withheld_amount = (approved_amount * withholding_pct) / 100
                new_result.adjudicated_amount = approved_amount - withheld_amount
                new_result.withheld_amount = withheld_amount

        new_result.save()

        # Add manual review messages
        self._add_override_messages(new_result, review_data)

        # Update claim status
        self.claim.status = 'A'
        self.claim.accepted_amount = approved_amount
        self.claim.adjudicated_amount = new_result.adjudicated_amount
        self.claim.reviewed_by = self.adjudicator
        self.claim.review_date = timezone.now()
        self.claim.save()

        # Deactivate previous results
        self._deactivate_previous_results(new_result)

        # Update service line amounts
        self._update_service_line_amounts(new_result)

        # Process financial transactions
        self._process_approval_transactions(new_result)

        logger.info(f"Claim {self.claim.transaction_number} manually approved for ${approved_amount}")

        return new_result

    def _manual_decline(self, review_data: Dict) -> AdjudicationResult:
        """Manually decline a claim"""

        # Create override record
        override = self._create_override_record(
            new_decision='DECLINED',
            new_amount=Decimal('0.00'),
            override_reason=review_data['override_reason'],
            review_notes=review_data.get('review_notes', '')
        )

        # Create new adjudication result
        new_result = AdjudicationResult.objects.create(
            claim=self.claim,
            result='DECLINED',
            claimed_amount=self.claim.claimed_amount,
            accepted_amount=Decimal('0.00'),
            adjudicated_amount=Decimal('0.00'),
            processing_type='MANUAL',
            processed_by=self.adjudicator,
            processed_at=timezone.now(),
            override_record=override,
            decline_reason=review_data['override_reason'],
            review_notes=review_data.get('review_notes', '')
        )

        # Add decline messages
        self._add_decline_messages(new_result, review_data)

        # Update claim status
        self.claim.status = 'D'
        self.claim.accepted_amount = Decimal('0.00')
        self.claim.adjudicated_amount = Decimal('0.00')
        self.claim.reviewed_by = self.adjudicator
        self.claim.review_date = timezone.now()
        self.claim.decline_reason = review_data['override_reason']
        self.claim.save()

        # Deactivate previous results
        self._deactivate_previous_results(new_result)

        # Release any reserved funds
        self._release_reserved_funds()

        logger.info(f"Claim {self.claim.transaction_number} manually declined: {review_data['override_reason']}")

        return new_result

    def _manual_modify(self, review_data: Dict) -> AdjudicationResult:
        """Manually modify claim amounts or conditions"""

        if 'override_amount' not in review_data:
            raise ValueError("Override amount required for modification")

        new_amount = review_data['override_amount']

        # Validate new amount
        if new_amount > self.claim.claimed_amount:
            raise ValueError("Override amount cannot exceed claimed amount")

        if new_amount < 0:
            raise ValueError("Override amount cannot be negative")

        # Create override record
        override = self._create_override_record(
            new_decision='MODIFIED',
            new_amount=new_amount,
            override_reason=review_data['override_reason'],
            review_notes=review_data.get('review_notes', '')
        )

        # Determine final result status
        result_status = 'APPROVED' if new_amount > 0 else 'DECLINED'

        # Create new adjudication result
        new_result = AdjudicationResult.objects.create(
            claim=self.claim,
            result=result_status,
            claimed_amount=self.claim.claimed_amount,
            accepted_amount=new_amount,
            adjudicated_amount=new_amount,
            processing_type='MANUAL',
            processed_by=self.adjudicator,
            processed_at=timezone.now(),
            override_record=override,
            review_notes=review_data.get('review_notes', ''),
            is_modified=True
        )

        # Handle additional conditions
        if 'additional_conditions' in review_data:
            new_result.additional_conditions = review_data['additional_conditions']
            new_result.save()

        # Add modification messages
        self._add_modification_messages(new_result, review_data)

        # Update claim
        self.claim.status = 'A' if new_amount > 0 else 'D'
        self.claim.accepted_amount = new_amount
        self.claim.adjudicated_amount = new_amount
        self.claim.reviewed_by = self.adjudicator
        self.claim.review_date = timezone.now()
        self.claim.save()

        # Deactivate previous results
        self._deactivate_previous_results(new_result)

        # Update service line amounts
        self._update_service_line_amounts(new_result)

        # Process financial transactions
        if new_amount > 0:
            self._process_approval_transactions(new_result)
        else:
            self._release_reserved_funds()

        logger.info(f"Claim {self.claim.transaction_number} manually modified to ${new_amount}")

        return new_result

    def _return_to_auto_adjudication(self, review_data: Dict) -> AdjudicationResult:
        """Return claim to automatic adjudication (e.g., after rule updates)"""

        # Create override record for tracking
        override = self._create_override_record(
            new_decision='RETURNED_TO_AUTO',
            new_amount=None,
            override_reason=review_data['override_reason'],
            review_notes=review_data.get('review_notes', '')
        )

        # Reset claim status
        self.claim.status = 'N'  # New status for re-processing
        self.claim.reviewed_by = self.adjudicator
        self.claim.review_date = timezone.now()
        self.claim.save()

        # Deactivate previous results
        if self.original_result:
            self.original_result.is_active = False
            self.original_result.save()

        # Re-run automatic adjudication
        from .auto_adjudication import process_claim_adjudication
        new_result = process_claim_adjudication(self.claim)

        # Link to override record
        new_result.override_record = override
        new_result.save()

        logger.info(f"Claim {self.claim.transaction_number} returned to auto-adjudication")

        return new_result

    def _create_override_record(self, new_decision: str, new_amount: Optional[Decimal],
                                override_reason: str, review_notes: str) -> AdjudicationOverride:
        """Create override tracking record"""

        return AdjudicationOverride.objects.create(
            claim=self.claim,
            adjudicator=self.adjudicator,
            original_result=self.original_result.result if self.original_result else None,
            original_amount=self.original_result.adjudicated_amount if self.original_result else None,
            new_decision=new_decision,
            new_amount=new_amount,
            override_reason=override_reason,
            review_notes=review_notes,
            override_timestamp=timezone.now()
        )

    def _add_override_messages(self, result: AdjudicationResult, review_data: Dict) -> None:
        """Add messages for manual override"""

        # Add manual approval message
        AdjudicationMessage.objects.create(
            adjudication_result=result,
            message_code=self._get_message_code('APPR002'),  # Manually Approved
            custom_description=f"Manually approved by {self.adjudicator.get_full_name()}"
        )

        # Add override reason
        if review_data.get('override_reason'):
            AdjudicationMessage.objects.create(
                adjudication_result=result,
                message_code=self._get_message_code('REVW002'),  # Manual Review
                custom_description=f"Override reason: {review_data['override_reason']}"
            )

        # Add any custom message codes
        if 'message_codes' in review_data:
            for code in review_data['message_codes']:
                message_code_obj = self._get_message_code(code)
                if message_code_obj:
                    AdjudicationMessage.objects.create(
                        adjudication_result=result,
                        message_code=message_code_obj
                    )

    def _add_decline_messages(self, result: AdjudicationResult, review_data: Dict) -> None:
        """Add messages for manual decline"""

        AdjudicationMessage.objects.create(
            adjudication_result=result,
            message_code=self._get_message_code('DECL003'),  # Incomplete Information
            custom_description=f"Manually declined: {review_data['override_reason']}"
        )

    def _add_modification_messages(self, result: AdjudicationResult, review_data: Dict) -> None:
        """Add messages for manual modification"""

        AdjudicationMessage.objects.create(
            adjudication_result=result,
            message_code=self._get_message_code('REVW002'),  # Manual Review
            custom_description=f"Amount modified to ${review_data['override_amount']} - {review_data['override_reason']}"
        )

    def _get_message_code(self, code: str) -> Optional[AdjudicationMessageCode]:
        """Get message code object"""
        try:
            return AdjudicationMessageCode.objects.get(code=code)
        except AdjudicationMessageCode.DoesNotExist:
            return None

    def _deactivate_previous_results(self, new_result: AdjudicationResult) -> None:
        """Deactivate previous adjudication results"""

        self.claim.adjudication_results.exclude(
            id=new_result.id
        ).update(is_active=False)

    def _update_service_line_amounts(self, result: AdjudicationResult) -> None:
        """Update service line amounts proportionally"""

        if self.claim.claimed_amount == 0:
            return

        adjustment_ratio = result.adjudicated_amount / self.claim.claimed_amount

        for service_line in self.claim.services.all():
            service_line.accepted_amount = service_line.claimed_amount
            service_line.adjudicated_amount = service_line.claimed_amount * adjustment_ratio
            service_line.save()

    def _process_approval_transactions(self, result: AdjudicationResult) -> None:
        """Process financial transactions for approved claims"""

        try:
            from accounting.models import MemberAccount, MemberTransaction

            account = self.claim.beneficiary.member.accounts.filter(
                currency=self.claim.beneficiary.member.currency
            ).first()

            if not account:
                logger.error(f"No account found for member {self.claim.beneficiary.member.membership_number}")
                return

            # Release any existing reservations
            existing_reserves = account.transactions.filter(
                claim=self.claim,
                transaction_type='R',
                status='C'
            )

            for reserve in existing_reserves:
                # Create unreserve transaction
                MemberTransaction.objects.create(
                    account=account,
                    transaction_type='U',  # Unreserve
                    amount_credited=reserve.amount_debited,
                    balance=account.balance,
                    available_balance=account.available_balance + reserve.amount_debited,
                    description=f'Release reserve for claim override: {self.claim.transaction_number}',
                    reference=f'OVERRIDE-{self.claim.transaction_number}',
                    claim=self.claim,
                    status='C'
                )

                # Update account balances
                account.available_balance += reserve.amount_debited
                account.reserved_balance -= reserve.amount_debited

            # Create new reservation for final amount
            if result.adjudicated_amount > 0:
                MemberTransaction.objects.create(
                    account=account,
                    transaction_type='R',  # Reserve
                    amount_debited=result.adjudicated_amount,
                    balance=account.balance,
                    available_balance=account.available_balance - result.adjudicated_amount,
                    description=f'Reserve for manually approved claim: {self.claim.transaction_number}',
                    reference=f'MANUAL-{self.claim.transaction_number}',
                    claim=self.claim,
                    status='C'
                )

                # Update account balances
                account.available_balance -= result.adjudicated_amount
                account.reserved_balance += result.adjudicated_amount

            account.save()

        except Exception as e:
            logger.error(f"Failed to process approval transactions: {str(e)}")

    def _release_reserved_funds(self) -> None:
        """Release any reserved funds for declined claims"""

        try:
            from accounting.models import MemberAccount, MemberTransaction

            account = self.claim.beneficiary.member.accounts.filter(
                currency=self.claim.beneficiary.member.currency
            ).first()

            if not account:
                return

            # Find and release reservations
            existing_reserves = account.transactions.filter(
                claim=self.claim,
                transaction_type='R',
                status='C'
            )

            for reserve in existing_reserves:
                # Create unreserve transaction
                MemberTransaction.objects.create(
                    account=account,
                    transaction_type='U',  # Unreserve
                    amount_credited=reserve.amount_debited,
                    balance=account.balance,
                    available_balance=account.available_balance + reserve.amount_debited,
                    description=f'Release reserve for declined claim: {self.claim.transaction_number}',
                    reference=f'DECLINE-{self.claim.transaction_number}',
                    claim=self.claim,
                    status='C'
                )

                # Update account balances
                account.available_balance += reserve.amount_debited
                account.reserved_balance -= reserve.amount_debited

            account.save()

        except Exception as e:
            logger.error(f"Failed to release reserved funds: {str(e)}")


# Bulk manual adjudication functions
def process_bulk_manual_review(claim_ids: List[int], review_data: Dict, adjudicator: User) -> Dict:
    """
    Process multiple claims for manual review

    Args:
        claim_ids: List of claim IDs to review
        review_data: Common review parameters to apply to all claims
        adjudicator: User performing the review
    """

    results = {
        'total_processed': 0,
        'approved': 0,
        'declined': 0,
        'modified': 0,
        'errors': 0,
        'details': []
    }

    claims = Claim.objects.filter(id__in=claim_ids)

    for claim in claims:
        try:
            engine = ManualAdjudicationEngine(claim, adjudicator)
            result = engine.review_claim(review_data)

            results['total_processed'] += 1

            if result.result == 'APPROVED':
                if result.is_modified:
                    results['modified'] += 1
                else:
                    results['approved'] += 1
            elif result.result == 'DECLINED':
                results['declined'] += 1

            results['details'].append({
                'claim_id': claim.id,
                'transaction_number': claim.transaction_number,
                'result': result.result,
                'amount': float(result.adjudicated_amount),
                'override_reason': review_data.get('override_reason', '')
            })

        except Exception as e:
            results['errors'] += 1
            results['details'].append({
                'claim_id': claim.id,
                'transaction_number': claim.transaction_number,
                'result': 'ERROR',
                'error': str(e)
            })

            logger.error(f"Bulk manual review error for claim {claim.id}: {str(e)}")

    logger.info(f"Bulk manual review completed by {adjudicator.username}: {results}")

    return results


# Quality assurance functions
def validate_adjudication_quality(adjudicator: User, days: int = 30) -> Dict:
    """
    Validate quality of adjudicator's decisions over specified period

    Args:
        adjudicator: The adjudicator to evaluate
        days: Number of days to look back
    """

    from datetime import timedelta

    start_date = timezone.now() - timedelta(days=days)

    # Get adjudicator's recent decisions
    recent_results = AdjudicationResult.objects.filter(
        processed_by=adjudicator,
        processed_at__gte=start_date,
        processing_type='MANUAL'
    )

    total_decisions = recent_results.count()

    if total_decisions == 0:
        return {'message': 'No recent decisions found'}

    # Calculate metrics
    approved = recent_results.filter(result='APPROVED').count()
    declined = recent_results.filter(result='DECLINED').count()
    modified = recent_results.filter(is_modified=True).count()

    # Calculate financial impact
    total_claimed = recent_results.aggregate(
        total=models.Sum('claimed_amount')
    )['total'] or Decimal('0')

    total_adjudicated = recent_results.aggregate(
        total=models.Sum('adjudicated_amount')
    )['total'] or Decimal('0')

    # Calculate average processing time (if tracked)
    # This would require additional timestamp fields

    quality_metrics = {
        'period_days': days,
        'total_decisions': total_decisions,
        'approval_rate': (approved / total_decisions) * 100,
        'decline_rate': (declined / total_decisions) * 100,
        'modification_rate': (modified / total_decisions) * 100,
        'total_claimed_amount': float(total_claimed),
        'total_adjudicated_amount': float(total_adjudicated),
        'savings_percentage': float(
            (total_claimed - total_adjudicated) / total_claimed * 100) if total_claimed > 0 else 0,
        'average_claim_value': float(total_adjudicated / total_decisions) if total_decisions > 0 else 0
    }

    return quality_metrics
