import logging
from decimal import Decimal

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from services.models import Claim, ServiceRequest, AdjudicationResult

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Claim)
def auto_adjudicate_claim(sender, instance, created, **kwargs):
    """Automatically adjudicate claims when created"""
    if created and instance.status == 'N':
        try:
            # from services.functions.adjudication import process_claim_adjudication

            # Process adjudication
            result = process_claim_adjudication(instance)

            logger.info(f"Auto-adjudicated claim {instance.transaction_number}: {result.get_result_display()}")

            # Send notification based on result
            if result.result == 'APPROVED':
                send_claim_approval_notification(instance)
            elif result.result == 'DECLINED':
                send_claim_decline_notification(instance, result.decline_reason)
            elif result.result in ['PENDING_REVIEW', 'PENDING_CLINICAL']:
                send_claim_review_notification(instance)

        except Exception as e:
            logger.error(f"Failed to auto-adjudicate claim {instance.transaction_number}: {str(e)}")


@receiver(post_save, sender=ServiceRequest)
def auto_adjudicate_service_request(sender, instance, created, **kwargs):
    """Automatically adjudicate service requests when created"""
    if created and instance.status == 'P':
        try:
            from services.functions.adjudication import process_service_request_adjudication

            # Process adjudication
            result = process_service_request_adjudication(instance)

            logger.info(f"Auto-adjudicated service request {instance.request_number}: {result.get_result_display()}")

            # Reserve funds if approved
            if result.result == 'APPROVED':
                reserve_funds_for_authorization(instance, result.adjudicated_amount)
                send_authorization_notification(instance)
            elif result.result == 'DECLINED':
                send_service_request_decline_notification(instance, result.decline_reason)

        except Exception as e:
            logger.error(f"Failed to auto-adjudicate service request {instance.request_number}: {str(e)}")


@receiver(post_save, sender=AdjudicationResult)
def handle_adjudication_result(sender, instance, created, **kwargs):
    """Handle adjudication results and trigger appropriate actions"""
    if not created:  # Only process updates, not creation
        try:
            if instance.result == 'APPROVED' and instance.processing_type == 'MANUAL':
                # Manual approval - send notifications
                if instance.claim:
                    send_manual_claim_approval(instance.claim, instance.processed_by)
                elif instance.service_request:
                    send_manual_authorization_approval(instance.service_request, instance.processed_by)

            elif instance.result == 'DECLINED':
                # Declined - send decline notifications
                if instance.claim:
                    send_manual_claim_decline(instance.claim, instance.decline_reason)
                elif instance.service_request:
                    send_manual_authorization_decline(instance.service_request, instance.decline_reason)

        except Exception as e:
            logger.error(f"Failed to handle adjudication result: {str(e)}")


@receiver(post_save, sender=Claim)
def create_claim_payment_method_transactions(sender, instance, created, **kwargs):
    """Create payment method transactions for claim payments and fees"""
    if not created and instance.status == 'P' and not hasattr(instance, '_pm_transactions_created'):
        try:
            from configurations.models import Currency
            from accounting.models import PaymentMethodAccount, PaymentMethodTransaction

            # Get the payment method used for this claim (member's preferred payment method)
            member = instance.beneficiary.member
            payment_method = getattr(member, 'preferred_payment_method', None)

            if payment_method:
                # Get payment method account
                try:
                    currency = Currency.objects.get(is_base_currency=True)
                except Currency.DoesNotExist:
                    currency = Currency.objects.filter(is_active=True).first()

                try:
                    pm_account = PaymentMethodAccount.objects.get(
                        payment_method=payment_method,
                        currency=currency
                    )

                    # Create claim payment transaction (debit from payment method)
                    if instance.adjudicated_amount and instance.adjudicated_amount > 0:
                        payment_transaction = PaymentMethodTransaction.objects.create(
                            account=pm_account,
                            transaction_type='claim_payment',
                            debited_amount=instance.adjudicated_amount,
                            description=f'Claim payment for {instance.transaction_number}',
                            reference_number=instance.transaction_number,
                            claim=instance,
                            status='C'
                        )
                        logger.info(f"Created claim payment transaction {payment_transaction.transaction_number}")

                    # Create processing fee transaction if applicable
                    if hasattr(instance, 'processing_fee') and instance.processing_fee > 0:
                        fee_transaction = PaymentMethodTransaction.objects.create(
                            account=pm_account,
                            transaction_type='claim_fee',
                            credited_amount=instance.processing_fee,
                            processing_fee=instance.processing_fee,
                            description=f'Claim processing fee from {instance.transaction_number}',
                            reference_number=instance.transaction_number,
                            claim=instance,
                            status='C'
                        )
                        logger.info(f"Created claim processing fee transaction {fee_transaction.transaction_number}")

                    # Mark as processed
                    instance._pm_transactions_created = True

                except PaymentMethodAccount.DoesNotExist:
                    logger.error(f"Payment method account not found for {payment_method.name}")

        except Exception as e:
            logger.error(f"Failed to create claim payment method transactions: {str(e)}")


@receiver(post_save, sender=Claim)
def create_agent_claim_commission(sender, instance, created, **kwargs):
    """Create agent commission for claim processing"""
    if not created and instance.status == 'P' and not hasattr(instance, '_commission_created'):
        try:
            # Check if the member was registered by an agent
            member = instance.beneficiary.member
            if member.registered_by:
                from configurations.models import AgentCommissionTerm, AgentCommission, Currency
                from accounting.models import AgentAccount, AgentTransaction

                agent = member.registered_by

                # Find applicable commission terms for claims
                active_terms = AgentCommissionTerm.objects.filter(
                    agent=agent,
                    is_active=True,
                    commission_type='claim_processing',
                    effective_from__lte=timezone.now().date()
                ).filter(
                    models.Q(effective_to__isnull=True) |
                    models.Q(effective_to__gte=timezone.now().date())
                )

                for term in active_terms:
                    # Create commission record
                    commission = AgentCommission.objects.create(
                        agent=agent,
                        commission_term=term,
                        member=member,
                        commission_type='claim_processing',
                        base_amount=instance.adjudicated_amount or instance.claimed_amount,
                        commission_rate=term.reward_percentage or agent.base_commission_rate,
                        period_from=timezone.now().date(),
                        period_to=timezone.now().date(),
                        status='C'
                    )

                    # Calculate commission amount
                    if term.reward_type == 'percentage':
                        commission.commission_amount = ((instance.adjudicated_amount or instance.claimed_amount) * term.reward_percentage) / 100
                    elif term.reward_type == 'fixed_amount':
                        commission.commission_amount = term.reward_fixed_amount
                    else:
                        commission.commission_amount = ((instance.adjudicated_amount or instance.claimed_amount) * agent.base_commission_rate) / 100

                    commission.save()

                    # Mark as processed
                    instance._commission_created = True

                    logger.info(f"Created claim commission {commission.commission_number} for agent {agent.name}")

        except Exception as e:
            logger.error(f"Failed to create agent claim commission: {str(e)}")


@receiver(post_save, sender=ServiceRequest)
def create_service_request_processing_fee_transaction(sender, instance, created, **kwargs):
    """Create payment method transaction for service request processing fees"""
    if not created and instance.status == 'A' and not hasattr(instance, '_fee_transaction_created'):
        try:
            # Check if there's a processing fee configuration
            from configurations.models import Currency
            from accounting.models import PaymentMethodAccount, PaymentMethodTransaction

            # Get the payment method used for this service request
            member = instance.beneficiary.member
            payment_method = getattr(member, 'preferred_payment_method', None)

            if payment_method and hasattr(instance, 'processing_fee') and instance.processing_fee > 0:
                # Get payment method account
                try:
                    currency = Currency.objects.get(is_base_currency=True)
                except Currency.DoesNotExist:
                    currency = Currency.objects.filter(is_active=True).first()

                try:
                    pm_account = PaymentMethodAccount.objects.get(
                        payment_method=payment_method,
                        currency=currency
                    )

                    # Create fee transaction
                    transaction = PaymentMethodTransaction.objects.create(
                        account=pm_account,
                        transaction_type='service_request_fee',
                        credited_amount=instance.processing_fee,
                        processing_fee=instance.processing_fee,
                        description=f'Service request processing fee from {instance.request_number}',
                        reference_number=instance.request_number,
                        service_request=instance,
                        status='C'
                    )

                    # Mark as processed
                    instance._fee_transaction_created = True

                    logger.info(f"Created service request processing fee transaction {transaction.transaction_number}")

                except PaymentMethodAccount.DoesNotExist:
                    logger.error(f"Payment method account not found for {payment_method.name}")

        except Exception as e:
            logger.error(f"Failed to create service request processing fee transaction: {str(e)}")


@receiver(post_save, sender=Claim)
def create_provider_payment_transaction(sender, instance, created, **kwargs):
    """Create provider transaction when claim is approved and paid"""
    if not created and instance.status == 'P' and not hasattr(instance, '_provider_payment_created'):
        try:
            # Check if claim has a service provider and adjudicated amount
            if instance.service_provider and instance.adjudicated_amount > 0:
                from configurations.models import Currency
                from accounting.models import ProviderAccount, ProviderTransaction

                # Get provider account
                try:
                    currency = Currency.objects.get(is_base_currency=True)
                except Currency.DoesNotExist:
                    currency = Currency.objects.filter(is_active=True).first()

                try:
                    provider_account = ProviderAccount.objects.get(
                        service_provider=instance.service_provider,
                        currency=currency
                    )

                    # Create provider payment transaction
                    transaction = ProviderTransaction.objects.create(
                        account=provider_account,
                        transaction_type='C',  # Claim Payment
                        credited_amount=instance.adjudicated_amount,
                        description=f'Claim payment for {instance.transaction_number}',
                        reference=instance.transaction_number,
                        claim=instance,
                        status='C'
                    )

                    # Mark as processed
                    instance._provider_payment_created = True

                    logger.info(f"Created provider payment transaction {transaction.transaction_number}")

                except ProviderAccount.DoesNotExist:
                    logger.error(f"Provider account not found for {instance.service_provider.name}")

        except Exception as e:
            logger.error(f"Failed to create provider payment transaction: {str(e)}")
