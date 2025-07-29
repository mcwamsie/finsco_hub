from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import models
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

from .models import (
    MemberAccount, MemberTransaction, 
    PaymentMethodAccount, PaymentMethodTransaction, PaymentMethodTransfer,
    AgentAccount, AgentTransaction, ProviderAccount, ProviderTransaction
)
from configurations.models import PaymentMethod, Agent, AgentCommission

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


@receiver(post_save, sender=PaymentMethodTransaction)
def update_payment_method_account_balances(sender, instance, created, **kwargs):
    """Update payment method account balances when transaction is created"""
    if created and instance.status == 'C':
        try:
            account = instance.account

            # Update balances based on transaction type
            if instance.transaction_type in ['top_up_fee', 'claim_fee', 'gateway_fee', 'adjustment']:
                if instance.credited_amount > 0:  # Credit transaction
                    account.current_balance += instance.credited_amount
                    account.available_balance += instance.credited_amount
                    account.total_credited += instance.credited_amount
                
                if instance.debited_amount > 0:  # Debit transaction
                    account.current_balance -= instance.debited_amount
                    account.available_balance -= instance.debited_amount
                    account.total_debited += instance.debited_amount

            elif instance.transaction_type == 'pending':
                # Move from available to pending
                account.available_balance -= instance.debited_amount
                account.pending_balance += instance.debited_amount

            elif instance.transaction_type == 'settlement':
                # Move from pending to settled
                account.pending_balance -= instance.credited_amount
                account.current_balance += instance.credited_amount

            # Update processing fees
            if instance.processing_fee > 0:
                account.total_processing_fees += instance.processing_fee

            # Update balance after transaction
            instance.balance_after = account.current_balance
            instance.available_balance_after = account.available_balance

            account.save()
            instance.save(update_fields=['balance_after', 'available_balance_after'])

            logger.info(f"Updated payment method account balances for transaction {instance.transaction_number}")

        except Exception as e:
            logger.error(f"Failed to update payment method account balances: {str(e)}")


@receiver(post_save, sender=AgentTransaction)
def update_agent_account_balances(sender, instance, created, **kwargs):
    """Update agent account balances when transaction is created"""
    if created and instance.status == 'C':
        try:
            account = instance.account

            # Update balances based on transaction type
            if instance.transaction_type in ['commission_earned', 'bonus', 'adjustment']:
                if instance.credited_amount > 0:  # Credit transaction
                    account.current_balance += instance.credited_amount
                    account.available_balance += instance.credited_amount
                    account.commission_balance += instance.credited_amount
                    account.total_credited += instance.credited_amount
                    
                    if instance.transaction_type == 'commission_earned':
                        account.total_commissions_earned += instance.credited_amount

            elif instance.transaction_type in ['commission_payout', 'deduction', 'withholding']:
                if instance.debited_amount > 0:  # Debit transaction
                    account.current_balance -= instance.debited_amount
                    account.available_balance -= instance.debited_amount
                    account.total_debited += instance.debited_amount
                    
                    if instance.transaction_type == 'commission_payout':
                        account.total_commissions_paid += instance.debited_amount
                        account.last_payout_date = timezone.now().date()

            # Handle withholding and deductions
            if instance.withholding_amount > 0:
                account.total_withholding += instance.withholding_amount

            if instance.deduction_amount > 0:
                account.total_deductions += instance.deduction_amount

            # Update pending commissions if related to commission
            if instance.agent_commission and instance.transaction_type == 'commission_earned':
                account.pending_commissions += instance.credited_amount

            # Update balance after transaction
            instance.balance_after = account.current_balance
            instance.commission_balance_after = account.commission_balance

            account.save()
            instance.save(update_fields=['balance_after', 'commission_balance_after'])

            logger.info(f"Updated agent account balances for transaction {instance.transaction_number}")

        except Exception as e:
            logger.error(f"Failed to update agent account balances: {str(e)}")


@receiver(post_save, sender=ProviderTransaction)
def update_provider_account_balances(sender, instance, created, **kwargs):
    """Update provider account balances when transaction is created"""
    if created and instance.status == 'C':
        try:
            account = instance.account

            # Update balances based on transaction type
            if instance.transaction_type in ['C', 'B', 'A', 'WR']:  # Credit transactions
                if instance.credited_amount > 0:
                    account.balance += instance.credited_amount
                    account.available_balance += instance.credited_amount
                    
            elif instance.transaction_type in ['W', 'F', 'P']:  # Debit transactions
                if instance.debited_amount > 0:
                    account.balance -= instance.debited_amount
                    account.available_balance -= instance.debited_amount
                    
            elif instance.transaction_type == 'WH':  # Withholding
                if instance.debited_amount > 0:
                    account.available_balance -= instance.debited_amount
                    account.withheld_balance += instance.debited_amount

            account.save()
            
            logger.info(f"Updated provider account balances for transaction {instance.transaction_number}")

        except Exception as e:
            logger.error(f"Failed to update provider account balances: {str(e)}")


@receiver(post_save, sender='configurations.PaymentMethod')
def create_payment_method_account(sender, instance, created, **kwargs):
    """Create payment method account when payment method is created"""
    if created:
        try:
            from configurations.models import Currency

            # Get default currency (base currency)
            try:
                currency = Currency.objects.get(is_base_currency=True)
            except Currency.DoesNotExist:
                currency = Currency.objects.filter(is_active=True).first()

            if currency:
                account, account_created = PaymentMethodAccount.objects.get_or_create(
                    payment_method=instance,
                    currency=currency,
                    defaults={
                        'current_balance': Decimal('0.00'),
                        'available_balance': Decimal('0.00'),
                        'pending_balance': Decimal('0.00'),
                        'status': 'A'
                    }
                )

                if account_created:
                    logger.info(f"Created account for payment method {instance.name}")

        except Exception as e:
            logger.error(f"Failed to create payment method account for {instance.name}: {str(e)}")


@receiver(post_save, sender='configurations.Agent')
def create_agent_account(sender, instance, created, **kwargs):
    """Create agent account when agent is created"""
    if created:
        try:
            from configurations.models import Currency

            # Get default currency (base currency)
            try:
                currency = Currency.objects.get(is_base_currency=True)
            except Currency.DoesNotExist:
                currency = Currency.objects.filter(is_active=True).first()

            if currency:
                account, account_created = AgentAccount.objects.get_or_create(
                    agent=instance,
                    currency=currency,
                    defaults={
                        'current_balance': Decimal('0.00'),
                        'available_balance': Decimal('0.00'),
                        'commission_balance': Decimal('0.00'),
                        'status': 'A'
                    }
                )

                if account_created:
                    logger.info(f"Created account for agent {instance.name}")

        except Exception as e:
            logger.error(f"Failed to create agent account for {instance.name}: {str(e)}")


@receiver(post_save, sender='configurations.AgentCommission')
def create_agent_commission_transaction(sender, instance, created, **kwargs):
    """Create agent transaction when commission is calculated"""
    if not created and instance.status == 'C' and not hasattr(instance, '_transaction_created'):
        try:
            from configurations.models import Currency

            # Get agent account
            try:
                currency = Currency.objects.get(is_base_currency=True)
            except Currency.DoesNotExist:
                currency = Currency.objects.filter(is_active=True).first()

            agent_account = AgentAccount.objects.get(
                agent=instance.agent,
                currency=currency
            )

            # Create commission transaction
            transaction = AgentTransaction.objects.create(
                account=agent_account,
                transaction_type='commission_earned',
                credited_amount=instance.commission_amount,
                description=f'Commission earned for {instance.commission_type}',
                reference_number=instance.commission_number,
                agent_commission=instance,
                commission_period_from=instance.period_from,
                commission_period_to=instance.period_to,
                status='C'
            )

            # Mark commission as processed to prevent duplicate transactions
            instance._transaction_created = True
            
            logger.info(f"Created commission transaction {transaction.transaction_number} for agent {instance.agent.name}")

        except AgentAccount.DoesNotExist:
            logger.error(f"Agent account not found for agent {instance.agent.name}")
        except Exception as e:
            logger.error(f"Failed to create commission transaction: {str(e)}")


@receiver(post_save, sender='membership.TopUp')
def create_payment_method_fee_transaction(sender, instance, created, **kwargs):
    """Create payment method transaction for top-up fees"""
    if not created and instance.status == 'S' and not hasattr(instance, '_fee_transaction_created'):
        try:
            if instance.payment_method and instance.processing_fee > 0:
                from configurations.models import Currency

                # Get payment method account
                try:
                    currency = Currency.objects.get(is_base_currency=True)
                except Currency.DoesNotExist:
                    currency = Currency.objects.filter(is_active=True).first()

                try:
                    pm_account = PaymentMethodAccount.objects.get(
                        payment_method=instance.payment_method,
                        currency=currency
                    )

                    # Create fee transaction
                    transaction = PaymentMethodTransaction.objects.create(
                        account=pm_account,
                        transaction_type='top_up_fee',
                        credited_amount=instance.processing_fee,
                        processing_fee=instance.processing_fee,
                        description=f'Top-up processing fee from {instance.top_up_number}',
                        reference_number=instance.top_up_number,
                        top_up=instance,
                        gateway_reference=instance.gateway_reference,
                        status='C'
                    )

                    # Mark as processed
                    instance._fee_transaction_created = True

                    logger.info(f"Created payment method fee transaction {transaction.transaction_number}")

                except PaymentMethodAccount.DoesNotExist:
                    logger.error(f"Payment method account not found for {instance.payment_method.name}")

        except Exception as e:
            logger.error(f"Failed to create payment method fee transaction: {str(e)}")


@receiver(pre_save, sender=AgentTransaction)
def calculate_agent_transaction_net_amount(sender, instance, **kwargs):
    """Calculate net amount for agent transactions before saving"""
    try:
        # Calculate net amount (credited - debited - withholding - deductions)
        net_amount = (instance.credited_amount - instance.debited_amount - 
                     instance.withholding_amount - instance.deduction_amount)
        instance.net_amount = net_amount

    except Exception as e:
        logger.error(f"Failed to calculate net amount for agent transaction: {str(e)}")


@receiver(pre_save, sender=PaymentMethodTransaction)
def update_payment_method_transaction_balances(sender, instance, **kwargs):
    """Update transaction balance fields before saving"""
    try:
        if instance.account:
            # These will be updated in post_save signal, but we set initial values here
            if not instance.balance_after:
                instance.balance_after = instance.account.current_balance
            if not instance.available_balance_after:
                instance.available_balance_after = instance.account.available_balance

    except Exception as e:
        logger.error(f"Failed to update payment method transaction balances: {str(e)}")


@receiver(pre_save, sender=AgentTransaction)
def update_agent_transaction_balances(sender, instance, **kwargs):
    """Update transaction balance fields before saving"""
    try:
        if instance.account:
            # These will be updated in post_save signal, but we set initial values here
            if not instance.balance_after:
                instance.balance_after = instance.account.current_balance
            if not instance.commission_balance_after:
                instance.commission_balance_after = instance.account.commission_balance

    except Exception as e:
        logger.error(f"Failed to update agent transaction balances: {str(e)}")


@receiver(pre_save, sender=ProviderTransaction)
def update_provider_transaction_balances(sender, instance, **kwargs):
    """Update transaction balance fields before saving"""
    try:
        if instance.account:
            # Set balance fields based on current account balance
            instance.balance_before = instance.account.balance
            
            # Calculate balance after based on transaction type
            if instance.transaction_type in ['C', 'B', 'A', 'WR']:  # Credit transactions
                instance.balance_after = instance.balance_before + (instance.credited_amount or 0)
            elif instance.transaction_type in ['W', 'F', 'P', 'WH']:  # Debit transactions
                instance.balance_after = instance.balance_before - (instance.debited_amount or 0)
            else:
                instance.balance_after = instance.balance_before

            # Set withheld balance fields
            instance.withheld_balance_before = instance.account.withheld_balance
            if instance.transaction_type == 'WH':  # Withholding
                instance.withheld_balance = instance.withheld_balance_before + (instance.debited_amount or 0)
            elif instance.transaction_type == 'WR':  # Withholding release
                instance.withheld_balance = instance.withheld_balance_before - (instance.credited_amount or 0)
            else:
                instance.withheld_balance = instance.withheld_balance_before

    except Exception as e:
        logger.error(f"Failed to update provider transaction balance fields: {str(e)}")


# PaymentMethodTransfer Signals

@receiver(post_save, sender=PaymentMethodTransfer)
def process_payment_method_transfer(sender, instance, created, **kwargs):
    """Process payment method transfer by creating corresponding transactions"""
    if not created and instance.status == 'C' and not hasattr(instance, '_transfer_processed'):
        try:
            # Create outgoing transaction (debit from source account)
            if not instance.from_transaction:
                from_transaction = PaymentMethodTransaction.objects.create(
                    account=instance.from_account,
                    transaction_type='transfer_out',
                    debited_amount=instance.amount,
                    processing_fee=instance.transfer_fee,
                    description=f'Transfer to {instance.to_account.payment_method.name} - {instance.transfer_number}',
                    reference_number=instance.transfer_number,
                    transfer_from_account=instance.to_account,
                    status='C'
                )
                instance.from_transaction = from_transaction

            # Create incoming transaction (credit to destination account)
            if not instance.to_transaction:
                to_transaction = PaymentMethodTransaction.objects.create(
                    account=instance.to_account,
                    transaction_type='transfer_in',
                    credited_amount=instance.amount,
                    description=f'Transfer from {instance.from_account.payment_method.name} - {instance.transfer_number}',
                    reference_number=instance.transfer_number,
                    transfer_to_account=instance.from_account,
                    status='C'
                )
                instance.to_transaction = to_transaction

            # Update transfer with transaction references
            instance._transfer_processed = True
            PaymentMethodTransfer.objects.filter(id=instance.id).update(
                from_transaction=instance.from_transaction,
                to_transaction=instance.to_transaction,
                processed_at=timezone.now()
            )

            logger.info(f"Processed payment method transfer {instance.transfer_number}")

        except Exception as e:
            logger.error(f"Failed to process payment method transfer {instance.transfer_number}: {str(e)}")


@receiver(post_save, sender=PaymentMethodTransfer)
def reverse_payment_method_transfer(sender, instance, **kwargs):
    """Handle transfer reversal by creating reversal transactions"""
    if instance.status == 'R' and not hasattr(instance, '_transfer_reversed'):
        try:
            # Create reversal transaction for source account (credit back)
            if instance.from_transaction:
                reversal_from = PaymentMethodTransaction.objects.create(
                    account=instance.from_account,
                    transaction_type='transfer_in',
                    credited_amount=instance.amount,
                    description=f'Reversal of transfer {instance.transfer_number}',
                    reference_number=f"REV-{instance.transfer_number}",
                    status='C'
                )

            # Create reversal transaction for destination account (debit back)
            if instance.to_transaction:
                reversal_to = PaymentMethodTransaction.objects.create(
                    account=instance.to_account,
                    transaction_type='transfer_out',
                    debited_amount=instance.amount,
                    description=f'Reversal of transfer {instance.transfer_number}',
                    reference_number=f"REV-{instance.transfer_number}",
                    status='C'
                )

            # Mark as reversed
            instance._transfer_reversed = True

            logger.info(f"Reversed payment method transfer {instance.transfer_number}")

        except Exception as e:
            logger.error(f"Failed to reverse payment method transfer {instance.transfer_number}: {str(e)}")


# Vendor Payment Signals

@receiver(post_save, sender=ProviderTransaction)
def create_provider_payment_method_transaction(sender, instance, created, **kwargs):
    """Create payment method transaction when provider is paid"""
    if not created and instance.status == 'C' and instance.transaction_type == 'C' and not hasattr(instance, '_payment_method_transaction_created'):
        try:
            # Check if provider has a preferred payment method
            if instance.account.payment_method and instance.amount_credited > 0:
                from configurations.models import Currency, Vendor
                from django.contrib.contenttypes.models import ContentType

                # Get base currency
                try:
                    currency = Currency.objects.get(is_base_currency=True)
                except Currency.DoesNotExist:
                    currency = Currency.objects.filter(is_active=True).first()

                # Get vendor record for this service provider
                vendor = None
                try:
                    content_type = ContentType.objects.get_for_model(instance.account.service_provider.__class__)
                    vendor = Vendor.objects.get(
                        content_type=content_type,
                        object_id=instance.account.service_provider.id
                    )
                except Vendor.DoesNotExist:
                    logger.warning(f"Vendor record not found for service provider {instance.account.service_provider.name}")

                # Get payment method account
                try:
                    pm_account = PaymentMethodAccount.objects.get(
                        payment_method=instance.account.payment_method,
                        currency=currency
                    )

                    # Create payment method transaction
                    transaction = PaymentMethodTransaction.objects.create(
                        account=pm_account,
                        transaction_type='provider_payment',
                        debited_amount=instance.amount_credited,
                        description=f'Payment to provider {instance.account.service_provider.name}',
                        reference_number=instance.transaction_number,
                        provider_transaction=instance,
                        vendor=vendor,
                        status='C'
                    )

                    # Mark as processed
                    instance._payment_method_transaction_created = True

                    logger.info(f"Created payment method transaction {transaction.transaction_number} for provider payment")

                except PaymentMethodAccount.DoesNotExist:
                    logger.error(f"Payment method account not found for {instance.account.payment_method.name}")

        except Exception as e:
            logger.error(f"Failed to create provider payment method transaction: {str(e)}")


@receiver(post_save, sender=AgentTransaction)
def create_agent_payment_method_transaction(sender, instance, created, **kwargs):
    """Create payment method transaction when agent commission is paid"""
    if not created and instance.status == 'C' and instance.transaction_type == 'commission_payout' and not hasattr(instance, '_payment_method_transaction_created'):
        try:
            # Check if agent has a preferred payment method
            if instance.account.preferred_payment_method and instance.credited_amount > 0:
                from configurations.models import Currency, Vendor
                from django.contrib.contenttypes.models import ContentType

                # Get base currency
                try:
                    currency = Currency.objects.get(is_base_currency=True)
                except Currency.DoesNotExist:
                    currency = Currency.objects.filter(is_active=True).first()

                # Get vendor record for this agent
                vendor = None
                try:
                    content_type = ContentType.objects.get_for_model(instance.account.agent.__class__)
                    vendor = Vendor.objects.get(
                        content_type=content_type,
                        object_id=instance.account.agent.id
                    )
                except Vendor.DoesNotExist:
                    logger.warning(f"Vendor record not found for agent {instance.account.agent.name}")

                # Get payment method account
                try:
                    pm_account = PaymentMethodAccount.objects.get(
                        payment_method=instance.account.preferred_payment_method,
                        currency=currency
                    )

                    # Create payment method transaction
                    transaction = PaymentMethodTransaction.objects.create(
                        account=pm_account,
                        transaction_type='agent_commission',
                        debited_amount=instance.credited_amount,
                        description=f'Commission payment to agent {instance.account.agent.name}',
                        reference_number=instance.transaction_number,
                        agent_transaction=instance,
                        vendor=vendor,
                        status='C'
                    )

                    # Mark as processed
                    instance._payment_method_transaction_created = True

                    logger.info(f"Created payment method transaction {transaction.transaction_number} for agent commission")

                except PaymentMethodAccount.DoesNotExist:
                    logger.error(f"Payment method account not found for {instance.account.preferred_payment_method.name}")

        except Exception as e:
            logger.error(f"Failed to create agent payment method transaction: {str(e)}")


@receiver(post_save, sender='configurations.AgentCommission')
def create_agent_commission_payment_method_transaction(sender, instance, created, **kwargs):
    """Create payment method transaction when agent commission is approved for payment"""
    if not created and instance.status == 'PD' and not hasattr(instance, '_payment_method_transaction_created'):
        try:
            # Check if agent has a preferred payment method
            if instance.agent.account.preferred_payment_method and instance.commission_amount > 0:
                from configurations.models import Currency, Vendor
                from django.contrib.contenttypes.models import ContentType

                # Get base currency
                try:
                    currency = Currency.objects.get(is_base_currency=True)
                except Currency.DoesNotExist:
                    currency = Currency.objects.filter(is_active=True).first()

                # Get vendor record for this agent
                vendor = None
                try:
                    content_type = ContentType.objects.get_for_model(instance.agent.__class__)
                    vendor = Vendor.objects.get(
                        content_type=content_type,
                        object_id=instance.agent.id
                    )
                except Vendor.DoesNotExist:
                    logger.warning(f"Vendor record not found for agent {instance.agent.name}")

                # Get payment method account
                try:
                    pm_account = PaymentMethodAccount.objects.get(
                        payment_method=instance.agent.account.preferred_payment_method,
                        currency=currency
                    )

                    # Create payment method transaction
                    transaction = PaymentMethodTransaction.objects.create(
                        account=pm_account,
                        transaction_type='agent_commission',
                        debited_amount=instance.commission_amount,
                        description=f'Commission payment to agent {instance.agent.name} - {instance.commission_number}',
                        reference_number=instance.commission_number,
                        vendor=vendor,
                        status='C'
                    )

                    # Mark as processed
                    instance._payment_method_transaction_created = True

                    logger.info(f"Created payment method transaction {transaction.transaction_number} for agent commission {instance.commission_number}")

                except PaymentMethodAccount.DoesNotExist:
                    logger.error(f"Payment method account not found for {instance.agent.account.preferred_payment_method.name}")

        except Exception as e:
            logger.error(f"Failed to create agent commission payment method transaction: {str(e)}")

