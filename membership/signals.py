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
