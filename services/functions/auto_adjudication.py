import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum

from services.models import (
    Claim, ClaimServiceLine, AdjudicationRule, AdjudicationResult,
    AdjudicationMessage, AdjudicationMessageCode
)
from membership.models import Beneficiary
from configurations.models import ServiceProvider, Service
from accounts.models import MemberAccount, MemberTransaction

logger = logging.getLogger(__name__)


class ClaimAdjudicationEngine:
    """
    VitalSuite Claims Adjudication Engine

    Processes claims through a comprehensive rule-based system that evaluates:
    - Beneficiary eligibility and limits
    - Service coverage and requirements
    - Provider compliance and authorization
    - Business rules and co-payments
    - Fraud detection patterns
    """

    def __init__(self, claim: Claim):
        self.claim = claim
        self.beneficiary = claim.beneficiary
        self.provider = claim.provider
        self.member = self.beneficiary.member
        self.messages = []
        self.total_claimed = Decimal('0.00')
        self.total_accepted = Decimal('0.00')
        self.total_adjudicated = Decimal('0.00')
        self.co_payment_amount = Decimal('0.00')
        self.result_status = 'PENDING'
        self.decline_reason = None

    def process_adjudication(self) -> AdjudicationResult:
        """Main adjudication process"""

        logger.info(f"Starting adjudication for claim {self.claim.transaction_number}")

        try:
            with transaction.atomic():
                # Step 1: Pre-validation checks
                if not self._pre_validation_checks():
                    return self._create_adjudication_result('DECLINED')

                # Step 2: Calculate totals from service lines
                self._calculate_claim_totals()

                # Step 3: Beneficiary eligibility checks
                if not self._check_beneficiary_eligibility():
                    return self._create_adjudication_result('DECLINED')

                # Step 4: Service coverage validation
                if not self._validate_service_coverage():
                    return self._create_adjudication_result('DECLINED')

                # Step 5: Provider compliance checks
                if not self._check_provider_compliance():
                    return self._create_adjudication_result('DECLINED')

                # Step 6: Authorization validation
                if not self._validate_authorization():
                    return self._create_adjudication_result('DECLINED')

                # Step 7: Apply business rules
                adjudication_result = self._apply_business_rules()
                if adjudication_result:
                    return adjudication_result

                # Step 8: Fraud detection
                fraud_flags = self._fraud_detection_checks()
                if fraud_flags:
                    return self._create_adjudication_result('PENDING_REVIEW')

                # Step 9: Account balance checks
                if not self._check_account_balance():
                    return self._create_adjudication_result('PENDING_REVIEW')

                # Step 10: Final approval
                return self._create_adjudication_result('APPROVED')

        except Exception as e:
            logger.error(f"Adjudication error for claim {self.claim.transaction_number}: {str(e)}")
            self._add_message('REVW001', f"System error during adjudication: {str(e)}")
            return self._create_adjudication_result('PENDING_REVIEW')

    def _pre_validation_checks(self) -> bool:
        """Pre-validation checks before starting adjudication"""

        # Check if claim already adjudicated
        if self.claim.status != 'N':
            self._add_message('REVW001', 'Claim already processed')
            return False

        # Check if claim has service lines
        if not self.claim.services.exists():
            self._add_message('SERV001', 'No services found on claim')
            return False

        # Check service dates
        for service_line in self.claim.services.all():
            days_old = (timezone.now().date() - service_line.service_date).days
            if days_old > 365:  # Configurable limit
                self._add_message('TIME001', f'Service date too old: {service_line.service_date}')
                return False

            if service_line.service_date > timezone.now().date():
                self._add_message('TIME002', f'Future service date: {service_line.service_date}')
                return False

        return True

    def _calculate_claim_totals(self) -> None:
        """Calculate claim totals from service lines"""

        service_lines = self.claim.services.all()

        for line in service_lines:
            self.total_claimed += line.claimed_amount

        logger.info(f"Claim totals - Claimed: {self.total_claimed}")

    def _check_beneficiary_eligibility(self) -> bool:
        """Check beneficiary eligibility and status"""

        # Check beneficiary status
        if self.beneficiary.status != 'A':
            if self.beneficiary.status == 'I':
                self._add_message('BENF001', 'Beneficiary account is inactive')
            elif self.beneficiary.status == 'S':
                self._add_message('BENF003', 'Beneficiary is suspended')
            elif self.beneficiary.status == 'T':
                self._add_message('BENF004', 'Beneficiary account terminated')
            return False

        # Check benefit start date
        if self.beneficiary.benefit_start_date and self.beneficiary.benefit_start_date > timezone.now().date():
            self._add_message('BENF002', f'Benefits start on {self.beneficiary.benefit_start_date}')
            return False

        # Check annual limits
        current_year_claims = self._get_current_year_utilization()
        remaining_limit = self.beneficiary.annual_limit - current_year_claims

        if remaining_limit <= 0:
            self._add_message('LIMT002', 'Annual limit exceeded')
            return False

        if self.total_claimed > remaining_limit:
            # Partial approval up to remaining limit
            self.total_accepted = remaining_limit
            self._add_message('LIMT001', f'Amount reduced to remaining annual limit: ${remaining_limit}')
        else:
            self.total_accepted = self.total_claimed

        self._add_message('BENF100', 'Beneficiary eligibility confirmed')
        return True

    def _validate_service_coverage(self) -> bool:
        """Validate service coverage and requirements"""

        for service_line in self.claim.services.all():
            service = service_line.service

            # Check if service is active
            if not service.is_active:
                self._add_message('SERV001', f'Service not covered: {service.description}')
                return False

            # Check package coverage
            if self.beneficiary.package:
                package_limits = self.beneficiary.package.limits.filter(
                    category=service.category
                )

                if not package_limits.exists():
                    self._add_message('PACK002', f'Service not covered under package: {service.description}')
                    return False

                # Check waiting period
                package_limit = package_limits.first()
                if package_limit.waiting_period_days > 0:
                    membership_days = (timezone.now().date() - self.beneficiary.benefit_start_date).days
                    if membership_days < package_limit.waiting_period_days:
                        self._add_message('PACK003', f'Service in waiting period: {service.description}')
                        return False

            # Check service requirements
            if service.requires_referral and not self.claim.referring_provider_number:
                self._add_message('SERV002', f'Referral required for: {service.description}')
                return False

            # Check age restrictions
            beneficiary_age = self._calculate_age(self.beneficiary.date_of_birth)

            # Pediatric services (under 18)
            if 'pediatric' in service.description.lower() and beneficiary_age >= 18:
                self._add_message('AGER001', f'Age restriction for pediatric service')
                return False

            # Geriatric services (over 65)
            if 'geriatric' in service.description.lower() and beneficiary_age < 65:
                self._add_message('AGER001', f'Age restriction for geriatric service')
                return False

        return True

    def _check_provider_compliance(self) -> bool:
        """Check service provider compliance and status"""

        # Check provider status
        if self.provider.status != 'A':
            if self.provider.status == 'I':
                self._add_message('PROV001', 'Service provider is inactive')
            elif self.provider.status == 'S':
                self._add_message('PROV002', 'Service provider is suspended')
            return False

        # Check provider documents
        missing_docs = []
        expired_docs = []

        required_docs = self.provider.type.requirements.filter(is_required=True)

        for requirement in required_docs:
            try:
                doc = self.provider.documents.get(document_type=requirement.document_type)
                if doc.is_expired:
                    expired_docs.append(doc.document_type.name)
            except:
                missing_docs.append(requirement.document_type.name)

        if missing_docs:
            self._add_message('PROV004', f'Missing documents: {", ".join(missing_docs)}')
            # May continue with payment withholding

        if expired_docs:
            self._add_message('PROV005', f'Expired documents: {", ".join(expired_docs)}')
            # May continue with payment withholding

        return True

    def _validate_authorization(self) -> bool:
        """Validate prior authorization if required"""

        # Check if any services require authorization
        services_requiring_auth = self.claim.services.filter(
            service__requires_authorization=True
        )

        if not services_requiring_auth.exists():
            return True

        if not self.claim.service_request:
            self._add_message('AUTH001', 'Prior authorization required')
            return False

        service_request = self.claim.service_request

        # Check authorization status
        if service_request.status != 'A':
            self._add_message('AUTH001', 'Valid authorization not found')
            return False

        # Check authorization expiry
        if service_request.is_expired:
            self._add_message('AUTH003', 'Authorization has expired')
            return False

        # Check remaining authorization amount
        if service_request.remaining_amount < self.total_accepted:
            if service_request.remaining_amount > 0:
                self.total_accepted = service_request.remaining_amount
                self._add_message('AUTH005', f'Partial authorization: ${service_request.remaining_amount}')
            else:
                self._add_message('AUTH004', 'Authorization fully utilized')
                return False

        self._add_message('AUTH002', f'Valid authorization: {service_request.authorization_code}')
        return True

    def _apply_business_rules(self) -> Optional[AdjudicationResult]:
        """Apply adjudication business rules"""

        # Get applicable rules ordered by priority
        rules = AdjudicationRule.objects.filter(
            is_active=True,
            effective_from__lte=timezone.now().date()
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=timezone.now().date())
        ).order_by('priority')

        for rule in rules:
            if self._rule_applies(rule):
                action_result = self._execute_rule_action(rule)
                if action_result:
                    return action_result

        return None

    def _rule_applies(self, rule: AdjudicationRule) -> bool:
        """Check if a rule applies to this claim"""

        # Check amount range
        if rule.min_amount and self.total_accepted < rule.min_amount:
            return False
        if rule.max_amount and self.total_accepted > rule.max_amount:
            return False

        # Check beneficiary type
        if rule.beneficiary_type and self.beneficiary.type not in rule.beneficiary_type.split(','):
            return False

        # Check member types
        if rule.member_types and self.member.type not in rule.member_types.split(','):
            return False

        # Check provider tiers
        if rule.provider_tiers.exists() and self.provider.tier not in rule.provider_tiers.all():
            return False

        # Check services
        claim_services = set(self.claim.services.values_list('service_id', flat=True))
        if rule.services.exists():
            rule_services = set(rule.services.values_list('id', flat=True))
            if not claim_services.intersection(rule_services):
                return False

        # Check categories
        claim_categories = set(self.claim.services.values_list('service__category_id', flat=True))
        if rule.categories.exists():
            rule_categories = set(rule.categories.values_list('id', flat=True))
            if not claim_categories.intersection(rule_categories):
                return False

        # Check age limits
        beneficiary_age = self._calculate_age(self.beneficiary.date_of_birth)
        if rule.min_age and beneficiary_age < rule.min_age:
            return False
        if rule.max_age and beneficiary_age > rule.max_age:
            return False

        # Check service frequency
        if rule.max_visits_per_year or rule.max_visits_per_month:
            # Count recent claims for same services
            recent_claims_count = self._count_recent_service_usage(rule)

            if rule.max_visits_per_year and recent_claims_count >= rule.max_visits_per_year:
                return False
            if rule.max_visits_per_month and recent_claims_count >= rule.max_visits_per_month:
                return False

        return True

    def _execute_rule_action(self, rule: AdjudicationRule) -> Optional[AdjudicationResult]:
        """Execute the action defined by the rule"""

        if rule.action == 'AUTO_APPROVE':
            self.result_status = 'APPROVED'

        elif rule.action == 'AUTO_DECLINE':
            self.result_status = 'DECLINED'
            self.decline_reason = rule.description
            self._add_message('DECL002', f'Policy exclusion: {rule.description}')
            return self._create_adjudication_result('DECLINED')

        elif rule.action == 'MANUAL_REVIEW':
            self.result_status = 'PENDING_REVIEW'
            self._add_message('REVW001', f'Manual review required: {rule.description}')
            return self._create_adjudication_result('PENDING_REVIEW')

        elif rule.action == 'CLINICAL_REVIEW':
            self.result_status = 'PENDING_CLINICAL'
            self._add_message('REVW002', f'Clinical review required: {rule.description}')
            return self._create_adjudication_result('PENDING_CLINICAL')

        elif rule.action == 'REDUCE_AMOUNT':
            if rule.reduction_percentage:
                reduction = (self.total_accepted * rule.reduction_percentage) / 100
                self.total_accepted -= reduction
                self._add_message('LIMT001', f'Amount reduced by {rule.reduction_percentage}%')
            elif rule.reduction_amount:
                self.total_accepted = min(self.total_accepted, rule.reduction_amount)
                self._add_message('LIMT001', f'Amount capped at ${rule.reduction_amount}')

        elif rule.action == 'APPLY_COPAYMENT':
            if rule.co_payment_percentage:
                self.co_payment_amount = (self.total_accepted * rule.co_payment_percentage) / 100
            elif rule.co_payment_amount:
                self.co_payment_amount = rule.co_payment_amount

            self.total_adjudicated = self.total_accepted - self.co_payment_amount
            self._add_message('PACK004', f'Co-payment applied: ${self.co_payment_amount}')

        return None

    def _fraud_detection_checks(self) -> List[str]:
        """Perform fraud detection checks"""

        fraud_flags = []

        # Check for duplicate claims
        duplicate_claims = Claim.objects.filter(
            beneficiary=self.beneficiary,
            provider=self.provider,
            invoice_number=self.claim.invoice_number,
            status__in=['A', 'P']
        ).exclude(id=self.claim.id)

        if duplicate_claims.exists():
            fraud_flags.append('DUPLICATE_CLAIM')
            self._add_message('FRAU001', 'Duplicate claim detected')

        # Check claim frequency (same provider, same day)
        same_day_claims = Claim.objects.filter(
            beneficiary=self.beneficiary,
            provider=self.provider,
            start_date=self.claim.start_date,
            status__in=['A', 'P']
        ).exclude(id=self.claim.id).count()

        if same_day_claims >= 3:
            fraud_flags.append('HIGH_FREQUENCY')
            self._add_message('FRAU002', 'High claim frequency detected')

        # Check unusually high amount
        avg_claim_amount = self._get_average_claim_amount()
        if avg_claim_amount and self.total_claimed > (avg_claim_amount * 5):
            fraud_flags.append('HIGH_AMOUNT')
            self._add_message('FRAU003', 'Unusually high claim amount')

        # Provider pattern checks
        provider_daily_claims = Claim.objects.filter(
            provider=self.provider,
            start_date=self.claim.start_date,
            status__in=['A', 'P']
        ).count()

        if provider_daily_claims > 50:  # Configurable threshold
            fraud_flags.append('PROVIDER_PATTERN')
            self._add_message('FRAU004', 'Unusual provider pattern detected')

        return fraud_flags

    def _check_account_balance(self) -> bool:
        """Check member account balance"""

        try:
            account = self.member.accounts.filter(
                currency=self.member.currency
            ).first()

            if not account:
                self._add_message('ACCT003', 'Member account not found')
                return False

            if account.available_balance < self.total_adjudicated:
                if account.available_balance > 0:
                    self.total_adjudicated = account.available_balance
                    self._add_message('ACCT001', f'Amount reduced to available balance: ${account.available_balance}')
                else:
                    self._add_message('ACCT002', 'Insufficient account balance')
                    return False

            return True

        except Exception as e:
            self._add_message('ACCT005', f'Account check failed: {str(e)}')
            return False

    def _create_adjudication_result(self, result: str) -> AdjudicationResult:
        """Create adjudication result record"""

        # Set final amounts
        if result == 'APPROVED':
            self.total_adjudicated = self.total_accepted - self.co_payment_amount
        elif result == 'DECLINED':
            self.total_adjudicated = Decimal('0.00')

        # Create adjudication result
        adjudication_result = AdjudicationResult.objects.create(
            claim=self.claim,
            result=result,
            claimed_amount=self.total_claimed,
            accepted_amount=self.total_accepted,
            adjudicated_amount=self.total_adjudicated,
            co_payment_amount=self.co_payment_amount,
            processing_type='AUTO',
            decline_reason=self.decline_reason
        )

        # Create messages
        for message_data in self.messages:
            AdjudicationMessage.objects.create(
                adjudication_result=adjudication_result,
                message_code=message_data['code'],
                custom_description=message_data['description']
            )

        # Update claim
        self.claim.accepted_amount = self.total_accepted
        self.claim.adjudicated_amount = self.total_adjudicated

        if result == 'APPROVED':
            self.claim.status = 'A'
            # Create member transaction to reserve funds
            self._create_member_transaction()
        elif result == 'DECLINED':
            self.claim.status = 'D'
        else:  # Pending review
            self.claim.status = 'U'

        self.claim.save()

        # Update service lines
        self._update_service_line_amounts()

        logger.info(f"Adjudication complete for claim {self.claim.transaction_number}: {result}")

        return adjudication_result

    def _create_member_transaction(self) -> None:
        """Create member transaction to reserve funds"""

        try:
            account = self.member.accounts.filter(
                currency=self.member.currency
            ).first()

            if account and self.total_adjudicated > 0:
                MemberTransaction.objects.create(
                    account=account,
                    transaction_type='R',  # Reserve
                    amount_debited=self.total_adjudicated,
                    balance=account.balance,
                    available_balance=account.available_balance - self.total_adjudicated,
                    description=f'Reserve for claim: {self.claim.transaction_number}',
                    reference=self.claim.transaction_number,
                    claim=self.claim,
                    status='C'
                )

                # Update account balances
                account.available_balance -= self.total_adjudicated
                account.reserved_balance += self.total_adjudicated
                account.save()

        except Exception as e:
            logger.error(f"Failed to create member transaction: {str(e)}")

    def _update_service_line_amounts(self) -> None:
        """Update service line amounts proportionally"""

        if self.total_claimed == 0:
            return

        adjustment_ratio = self.total_adjudicated / self.total_claimed

        for service_line in self.claim.services.all():
            service_line.accepted_amount = service_line.claimed_amount
            service_line.adjudicated_amount = service_line.claimed_amount * adjustment_ratio
            service_line.save()

    def _add_message(self, code: str, description: str) -> None:
        """Add adjudication message"""

        self.messages.append({
            'code': code,
            'description': description
        })

    def _get_current_year_utilization(self) -> Decimal:
        """Get beneficiary utilization for current year"""

        current_year = timezone.now().year

        utilization = Claim.objects.filter(
            beneficiary=self.beneficiary,
            start_date__year=current_year,
            status__in=['A', 'P']
        ).aggregate(
            total=Sum('adjudicated_amount')
        )['total'] or Decimal('0.00')

        return utilization

    def _calculate_age(self, birth_date) -> int:
        """Calculate age from birth date"""

        today = timezone.now().date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    def _count_recent_service_usage(self, rule: AdjudicationRule) -> int:
        """Count recent service usage for frequency checks"""

        from datetime import timedelta

        if rule.max_visits_per_month:
            start_date = timezone.now().date() - timedelta(days=30)
        else:
            start_date = timezone.now().date() - timedelta(days=365)

        claim_services = self.claim.services.values_list('service_id', flat=True)

        usage_count = Claim.objects.filter(
            beneficiary=self.beneficiary,
            start_date__gte=start_date,
            status__in=['A', 'P'],
            services__service_id__in=claim_services
        ).distinct().count()

        return usage_count

    def _get_average_claim_amount(self) -> Optional[Decimal]:
        """Get average claim amount for beneficiary"""

        from datetime import timedelta

        six_months_ago = timezone.now().date() - timedelta(days=180)

        avg_amount = Claim.objects.filter(
            beneficiary=self.beneficiary,
            start_date__gte=six_months_ago,
            status__in=['A', 'P']
        ).aggregate(
            avg=models.Avg('adjudicated_amount')
        )['avg']

        return avg_amount


# Main adjudication function
def process_claim_adjudication(claim: Claim) -> AdjudicationResult:
    """
    Main function to process claim adjudication

    Args:
        claim: The claim to be adjudicated

    Returns:
        AdjudicationResult: The adjudication result with decision and amounts
    """

    engine = ClaimAdjudicationEngine(claim)
    return engine.process_adjudication()


# Service Request Adjudication (for pre-authorization)
def process_service_request_adjudication(service_request) -> AdjudicationResult:
    """
    Process service request (pre-authorization) adjudication

    Similar to claim adjudication but for pre-authorization requests
    """

    from services.models import ServiceRequest

    # Create temporary claim-like object for processing
    temp_claim = type('obj', (object,), {
        'beneficiary': service_request.beneficiary,
        'provider': service_request.service_provider,
        'services': service_request.items,
        'transaction_number': service_request.request_number,
        'start_date': service_request.proposed_service_date,
        'status': 'N'
    })

    # Use simplified adjudication for pre-auth
    engine = ClaimAdjudicationEngine(temp_claim)
    engine.total_claimed = service_request.estimated_amount

    # Run key checks
    if not engine._check_beneficiary_eligibility():
        result = 'DECLINED'
    elif not engine._validate_service_coverage():
        result = 'DECLINED'
    elif not engine._check_provider_compliance():
        result = 'PENDING_REVIEW'
    else:
        result = 'APPROVED'

    # Create result for service request
    adjudication_result = AdjudicationResult.objects.create(
        service_request=service_request,
        result=result,
        claimed_amount=service_request.estimated_amount,
        accepted_amount=engine.total_accepted,
        adjudicated_amount=engine.total_accepted,
        processing_type='AUTO'
    )

    # Update service request
    if result == 'APPROVED':
        service_request.status = 'A'
        service_request.approved_amount = engine.total_accepted
        # Generate authorization code
        from sequences import Sequence
        sequence_number = Sequence("authorization_code").get_next_value()
        service_request.authorization_code = f"AUTH{sequence_number:06d}"
    elif result == 'DECLINED':
        service_request.status = 'D'
    else:
        service_request.status = 'U'

    service_request.save()

    return adjudication_result


# Batch adjudication for multiple claims
def process_batch_adjudication(claim_ids: List[int]) -> Dict:
    """
    Process multiple claims in batch

    Args:
        claim_ids: List of claim IDs to process

    Returns:
        Dict: Summary of batch processing results
    """

    results = {
        'total_processed': 0,
        'approved': 0,
        'declined': 0,
        'pending_review': 0,
        'pending_clinical': 0,
        'errors': 0,
        'details': []
    }

    claims = Claim.objects.filter(id__in=claim_ids, status='N')

    for claim in claims:
        try:
            adjudication_result = process_claim_adjudication(claim)

            results['total_processed'] += 1

            if adjudication_result.result == 'APPROVED':
                results['approved'] += 1
            elif adjudication_result.result == 'DECLINED':
                results['declined'] += 1
            elif adjudication_result.result == 'PENDING_REVIEW':
                results['pending_review'] += 1
            elif adjudication_result.result == 'PENDING_CLINICAL':
                results['pending_clinical'] += 1

            results['details'].append({
                'claim_id': claim.id,
                'transaction_number': claim.transaction_number,
                'result': adjudication_result.result,
                'claimed_amount': float(adjudication_result.claimed_amount),
                'adjudicated_amount': float(adjudication_result.adjudicated_amount)
            })

        except Exception as e:
            results['errors'] += 1
            results['details'].append({
                'claim_id': claim.id,
                'transaction_number': claim.transaction_number,
                'result': 'ERROR',
                'error': str(e)
            })

            logger.error(f"Batch adjudication error for claim {claim.id}: {str(e)}")

    logger.info(f"Batch adjudication completed: {results}")
