import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accounting.models import MemberTransaction
from membership.models import Beneficiary, TopUp

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Beneficiary)
def update_member_limits(sender, instance, created, **kwargs):
    """Update member limits when beneficiary is added"""
    if created:
        try:
            member = instance.member

            # Calculate total beneficiaries
            total_beneficiaries = member.beneficiaries.filter(status='A').count()

            # Adjust member limits based on family size
            if member.default_package:
                package = member.default_package

                # Update global family limit if applicable
                if package.global_family_limit > 0:
                    # Distribute family limit among beneficiaries
                    per_beneficiary_limit = package.global_family_limit / total_beneficiaries

                    # Update all beneficiaries' limits
                    member.beneficiaries.filter(status='A').update(
                        annual_limit=min(per_beneficiary_limit, package.global_annual_limit)
                    )

                    logger.info(
                        f"Updated limits for {total_beneficiaries} beneficiaries of member {member.membership_number}")

        except Exception as e:
            logger.error(f"Failed to update member limits: {str(e)}")


@receiver(post_save, sender=TopUp)
def process_successful_topup(sender, instance, created, **kwargs):
    """Process successful top-up payments"""
    if not created and instance.status == 'S' and not hasattr(instance, '_processed'):
        try:
            # Create member transaction
            transaction = MemberTransaction.objects.create(
                account=instance.account,
                transaction_type='T',
                amount_credited=instance.net_amount,
                balance=instance.account.balance + instance.net_amount,
                available_balance=instance.account.available_balance + instance.net_amount,
                description=f'Top-up via {instance.payment_method.name}',
                reference=instance.top_up_number,
                top_up=instance,
                status='C'
            )

            # Update account balance
            instance.account.balance += instance.net_amount
            instance.account.available_balance += instance.net_amount
            instance.account.save()

            # Set completion date
            instance.completed_date = timezone.now()
            instance._processed = True  # Prevent recursive processing
            instance.save()

            logger.info(f"Processed top-up {instance.top_up_number} for {instance.net_amount}")

            # Send confirmation to member
            send_topup_confirmation(instance)

        except Exception as e:
            logger.error(f"Failed to process top-up {instance.top_up_number}: {str(e)}")


@receiver(post_save, sender=TopUp)
def create_payment_method_transactions(sender, instance, created, **kwargs):
    """Create payment method transactions for top-up amounts and fees"""
    if not created and instance.status == 'S' and not hasattr(instance, '_pm_transactions_created'):
        try:
            from configurations.models import Currency
            from accounting.models import PaymentMethodAccount, PaymentMethodTransaction

            # Get the payment method used for this top-up
            payment_method = instance.payment_method

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

                    # Create top-up amount transaction (credit to payment method)
                    if instance.amount > 0:
                        amount_transaction = PaymentMethodTransaction.objects.create(
                            account=pm_account,
                            transaction_type='top_up',
                            credited_amount=instance.amount,
                            description=f'Top-up amount from {instance.transaction_number}',
                            reference_number=instance.transaction_number,
                            top_up=instance,
                            status='C'
                        )
                        logger.info(f"Created top-up amount transaction {amount_transaction.transaction_number}")

                    # Create processing fee transaction if applicable
                    if hasattr(instance, 'processing_fee') and instance.processing_fee > 0:
                        fee_transaction = PaymentMethodTransaction.objects.create(
                            account=pm_account,
                            transaction_type='top_up_fee',
                            credited_amount=instance.processing_fee,
                            processing_fee=instance.processing_fee,
                            description=f'Top-up processing fee from {instance.transaction_number}',
                            reference_number=instance.transaction_number,
                            top_up=instance,
                            status='C'
                        )
                        logger.info(f"Created top-up fee transaction {fee_transaction.transaction_number}")

                    # Mark as processed
                    instance._pm_transactions_created = True

                except PaymentMethodAccount.DoesNotExist:
                    logger.error(f"Payment method account not found for {payment_method.name}")

        except Exception as e:
            logger.error(f"Failed to create payment method transactions: {str(e)}")
