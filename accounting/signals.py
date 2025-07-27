import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from accounting.models import MemberTransaction

logger = logging.getLogger(__name__)

@receiver(post_save, sender=MemberTransaction)
def update_account_balances(sender, instance, created, **kwargs):
    """Update account balances when transaction is created"""
    if created and instance.status == 'C':
        try:
            account = instance.account

            # Update balances based on transaction type
            if instance.transaction_type in ['D', 'T', 'RF', 'TR']:  # Credits
                account.balance += instance.amount_credited
                account.available_balance += instance.amount_credited
            elif instance.transaction_type in ['C', 'W', 'F', 'TO']:  # Debits
                account.balance -= instance.amount_debited
                account.available_balance -= instance.amount_debited
            elif instance.transaction_type == 'R':  # Reserve
                account.available_balance -= instance.amount_debited
                account.reserved_balance += instance.amount_debited
            elif instance.transaction_type == 'U':  # Unreserve
                account.available_balance += instance.amount_credited
                account.reserved_balance -= instance.amount_credited

            account.save()

            logger.info(f"Updated account balances for transaction {instance.transaction_number}")

        except Exception as e:
            logger.error(f"Failed to update account balances: {str(e)}")

