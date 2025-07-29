from django.db import models
from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
import logging

from .models import (
    Member, Agent, ServiceProvider, ServiceProviderDocument,
    ServiceProviderTypeRequirement, Currency, PaymentMethod, AgentCommission, Vendor
)
from membership.models import Beneficiary
# from accounts.models import MemberAccount, MemberTransaction, TopUp
from services.models import Claim, ServiceRequest, AdjudicationResult

logger = logging.getLogger(__name__)


# Member-related signals
@receiver(post_save, sender=Member)
def create_member_account(sender, instance, created, **kwargs):
    """Create default member account when member is created"""
    if created:
        try:
            from accounting.models import MemberAccount

            # Create account in member's currency
            account, account_created = MemberAccount.objects.get_or_create(
                member=instance,
                currency=instance.currency,
                defaults={
                    'balance': Decimal('0.00'),
                    'available_balance': Decimal('0.00'),
                    'reserved_balance': Decimal('0.00'),
                    'status': 'A'
                }
            )

            if account_created:
                logger.info(f"Created account for member {instance.membership_number}")

                # If member has parent, link accounts
                if instance.parent and instance.parent.accounts.exists():
                    parent_account = instance.parent.accounts.filter(
                        currency=instance.currency
                    ).first()
                    if parent_account:
                        account.parent_account = parent_account
                        account.save()
                        logger.info(f"Linked sub-member account to parent: {instance.parent.membership_number}")

        except Exception as e:
            logger.error(f"Failed to create account for member {instance.membership_number}: {str(e)}")
    else:
        try:
            from accounting.models import MemberAccount

            try:
                account = MemberAccount.objects.get( member=instance,
                currency=instance.currency,)
            except MemberAccount.DoesNotExist:
                account = MemberAccount.objects.create(
                    member=instance,
                    currency=instance.currency,
                    balance=Decimal('0.00'),
                    available_balance=Decimal('0.00'),
                    reserved_balance=Decimal('0.00'),
                    status='A'
                )
                logger.info(f"Created account for member {instance.membership_number}")

                # If member has parent, link accounts
                if instance.parent and instance.parent.accounts.exists():
                    parent_account = instance.parent.accounts.filter(
                        currency=instance.currency
                    ).first()
                    if parent_account:
                        account.parent_account = parent_account
                        account.save()
                        logger.info(f"Linked sub-member account to parent: {instance.parent.membership_number}")

        except Exception as e:
            logger.error(f"Failed to create account for member {instance.membership_number}: {str(e)}")


@receiver(post_save, sender=Member)
def create_principal_beneficiary(sender, instance, created, **kwargs):
    """Create principal beneficiary when member is created"""
    if created and not instance.parent:  # Only for main members, not sub-members
        try:
            # Create principal beneficiary
            beneficiary = Beneficiary.objects.create(
                first_name=instance.name.split()[0] if instance.name.split() else "Principal",
                last_name=instance.name.split()[-1] if len(instance.name.split()) > 1 else "Member",
                national_id_number=instance.identification_no or f"TEMP-{instance.membership_number}",
                date_of_birth=timezone.now().date(),  # Will need to be updated
                gender='M',  # Default, will need to be updated
                member=instance,
                type='P',
                status='A',
                annual_limit=instance.global_annual_limit,
                package=instance.default_package
            )

            logger.info(f"Created principal beneficiary for member {instance.membership_number}")

        except Exception as e:
            logger.error(f"Failed to create principal beneficiary for {instance.membership_number}: {str(e)}")


@receiver(post_save, sender=Member)
def calculate_agent_commission(sender, instance, created, **kwargs):
    """Calculate agent commission when member is registered"""
    if created and instance.registered_by:
        try:
            from .models import AgentCommission, AgentCommissionTerm

            agent = instance.registered_by

            # Find applicable commission terms
            active_terms = AgentCommissionTerm.objects.filter(
                agent=agent,
                is_active=True,
                effective_from__lte=timezone.now().date()
            ).filter(
                models.Q(effective_to__isnull=True) |
                models.Q(effective_to__gte=timezone.now().date())
            )

            for term in active_terms:
                # Check if member type matches term
                if term.member_types:
                    allowed_types = [t.strip() for t in term.member_types.split(',')]
                    if instance.type not in allowed_types:
                        continue

                # Create commission record
                commission = AgentCommission.objects.create(
                    agent=agent,
                    commission_term=term,
                    member=instance,
                    commission_type='registration',
                    base_amount=instance.global_annual_limit,
                    commission_rate=term.reward_percentage or agent.base_commission_rate,
                    period_from=timezone.now().date(),
                    period_to=timezone.now().date(),
                    status='P'
                )

                # Calculate commission amount
                if term.reward_type == 'percentage':
                    commission.commission_amount = (instance.global_annual_limit * term.reward_percentage) / 100
                elif term.reward_type == 'fixed_amount':
                    commission.commission_amount = term.reward_fixed_amount
                else:
                    commission.commission_amount = (instance.global_annual_limit * agent.base_commission_rate) / 100

                commission.save()

                logger.info(f"Created commission {commission.commission_number} for agent {agent.name}")

        except Exception as e:
            logger.error(f"Failed to calculate commission for member {instance.membership_number}: {str(e)}")


@receiver(post_save, sender=Member)
def check_agent_commission_thresholds(sender, instance, created, **kwargs):
    """Check if agent has reached commission thresholds"""
    if created and instance.registered_by:
        try:
            from .models import AgentCommissionTerm, AgentCommission

            agent = instance.registered_by

            # Check threshold-based terms
            threshold_terms = AgentCommissionTerm.objects.filter(
                agent=agent,
                is_active=True,
                condition_type__in=['member_count', 'beneficiary_count'],
                effective_from__lte=timezone.now().date()
            ).filter(
                models.Q(effective_to__isnull=True) |
                models.Q(effective_to__gte=timezone.now().date())
            )

            for term in threshold_terms:
                current_count = 0

                if term.condition_type == 'member_count':
                    current_count = Member.objects.filter(registered_by=agent).count()
                elif term.condition_type == 'beneficiary_count':
                    current_count = Beneficiary.objects.filter(
                        member__registered_by=agent
                    ).count()

                # Check if threshold reached
                if current_count >= term.threshold_value:
                    # Check if bonus already awarded
                    existing_bonus = AgentCommission.objects.filter(
                        agent=agent,
                        commission_term=term,
                        commission_type='bonus',
                        status__in=['C', 'A', 'PD']
                    ).exists()

                    if not existing_bonus:
                        # Award bonus
                        bonus = AgentCommission.objects.create(
                            agent=agent,
                            commission_term=term,
                            commission_type='bonus',
                            base_amount=term.threshold_value,
                            commission_amount=term.reward_fixed_amount,
                            period_from=timezone.now().date(),
                            period_to=timezone.now().date(),
                            status='C'
                        )

                        logger.info(f"Awarded threshold bonus {bonus.commission_number} to agent {agent.name}")

                        # Send notification
                        send_agent_bonus_notification(agent, bonus)

        except Exception as e:
            logger.error(f"Failed to check commission thresholds: {str(e)}")


@receiver(post_save, sender=Agent)
def create_agent_account(sender, instance, created, **kwargs):
    """Create agent account when agent is created"""
    if created:
        try:
            from accounting.models import AgentAccount

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


@receiver(post_save, sender=PaymentMethod)
def create_payment_method_account(sender, instance, created, **kwargs):
    """Create payment method account when payment method is created"""
    if created:
        try:
            from accounting.models import PaymentMethodAccount

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


@receiver(post_save, sender=AgentCommission)
def create_agent_commission_transaction(sender, instance, created, **kwargs):
    """Create agent transaction when commission is calculated"""
    if not created and instance.status == 'C' and not hasattr(instance, '_transaction_created'):
        try:
            from accounting.models import AgentAccount, AgentTransaction

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


@receiver(post_save, sender=ServiceProvider)
def create_provider_account(sender, instance, created, **kwargs):
    """Create provider account when service provider is created"""
    if created:
        try:
            from accounting.models import ProviderAccount
            from .models import Currency

            # Get default currency (USD or base currency)
            try:
                currency = Currency.objects.get(is_base_currency=True)
            except Currency.DoesNotExist:
                currency = Currency.objects.get(code='USD')

            account, account_created = ProviderAccount.objects.get_or_create(
                service_provider=instance,
                currency=currency,
                defaults={
                    'balance': Decimal('0.00'),
                    'available_balance': Decimal('0.00'),
                    'withheld_balance': Decimal('0.00'),
                    'status': 'A'
                }
            )

            if account_created:
                logger.info(f"Created account for provider {instance.account_no}")

        except Exception as e:
            logger.error(f"Failed to create provider account for {instance.account_no}: {str(e)}")


@receiver(post_save, sender=ServiceProviderDocument)
def check_document_compliance(sender, instance, created, **kwargs):
    """Check provider compliance when document is uploaded or updated"""
    try:
        provider = instance.service_provider

        # Get all requirements for this provider type
        requirements = ServiceProviderTypeRequirement.objects.filter(
            provider_type=provider.type,
            is_required=True
        )

        compliance_issues = []
        missing_docs = []
        expired_docs = []

        for requirement in requirements:
            try:
                doc = ServiceProviderDocument.objects.get(
                    service_provider=provider,
                    document_type=requirement.document_type
                )

                # Check if expired
                if doc.is_expired and requirement.withhold_payment_if_expired:
                    expired_docs.append(requirement.document_type)
                    compliance_issues.append(f"Expired: {requirement.document_type.name}")

            except ServiceProviderDocument.DoesNotExist:
                if requirement.withhold_payment_if_missing:
                    missing_docs.append(requirement.document_type)
                    compliance_issues.append(f"Missing: {requirement.document_type.name}")

        # Update provider compliance status
        if compliance_issues:
            logger.warning(f"Compliance issues for provider {provider.account_no}: {compliance_issues}")

            # Send notification to provider
            send_compliance_notification(provider, compliance_issues)

            # Update provider status if needed
            if len(compliance_issues) >= 3:  # Threshold for suspension
                provider.status = 'S'  # Suspended
                provider.save()
                logger.warning(f"Provider {provider.account_no} suspended due to compliance issues")

    except Exception as e:
        logger.error(f"Failed to check document compliance: {str(e)}")


@receiver(pre_save, sender=ServiceProviderDocument)
def check_document_expiry_alerts(sender, instance, **kwargs):
    """Send alerts for documents nearing expiry"""
    if instance.expiry_date and instance.document_type.reminder_days_before_expiry:
        try:
            from datetime import timedelta

            warning_date = instance.expiry_date - timedelta(
                days=instance.document_type.reminder_days_before_expiry
            )

            if timezone.now().date() >= warning_date and not instance.is_expired:
                # Send expiry warning
                send_document_expiry_warning(instance)
                logger.info(f"Sent expiry warning for document {instance.document_type.name}")

        except Exception as e:
            logger.error(f"Failed to send expiry warning: {str(e)}")


@receiver(post_save, sender='configurations.MemberKYCDocument')
def check_member_kyc_completion(sender, instance, created, **kwargs):
    """Check if member KYC is complete when document is verified"""
    if instance.status == 'V':  # Verified
        try:
            member = instance.member

            # Get all mandatory requirements for this member type
            mandatory_requirements = sender.objects.filter(
                requirement__member_types__contains=member.type,
                requirement__is_mandatory=True
            ).values_list('requirement_id', flat=True)

            # Check if all mandatory documents are verified
            verified_requirements = member.kyc_documents.filter(
                status='V',
                requirement_id__in=mandatory_requirements
            ).values_list('requirement_id', flat=True)

            if set(mandatory_requirements) <= set(verified_requirements):
                # All mandatory KYC complete
                member.kyc_verified_at = timezone.now()
                member.save()

                logger.info(f"KYC completed for member {member.membership_number}")

                # Send KYC completion notification
                send_kyc_completion_notification(member)

        except Exception as e:
            logger.error(f"Failed to check KYC completion: {str(e)}")


# Vendor Creation Signals

@receiver(post_save, sender=ServiceProvider)
def create_vendor_for_service_provider(sender, instance, created, **kwargs):
    """Create vendor record when service provider is created"""
    if created:
        try:
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(ServiceProvider)
            
            vendor, vendor_created = Vendor.objects.get_or_create(
                content_type=content_type,
                object_id=instance.id,
                defaults={
                    'vendor_type': 'SP',
                    'vendor_name': instance.name,
                    'contact_person': instance.contact_person,
                    'email': instance.email,
                    'phone': instance.phone,
                    'preferred_payment_method': instance.payment_method,
                    'tax_id': instance.tax_id,
                    'is_active': instance.status == 'A'
                }
            )
            
            if vendor_created:
                logger.info(f"Created vendor record {vendor.vendor_code} for service provider {instance.name}")
                
        except Exception as e:
            logger.error(f"Failed to create vendor for service provider {instance.name}: {str(e)}")


@receiver(post_save, sender=Agent)
def create_vendor_for_agent(sender, instance, created, **kwargs):
    """Create vendor record when agent is created"""
    if created:
        try:
            from django.contrib.contenttypes.models import ContentType
            
            content_type = ContentType.objects.get_for_model(Agent)
            
            vendor, vendor_created = Vendor.objects.get_or_create(
                content_type=content_type,
                object_id=instance.id,
                defaults={
                    'vendor_type': 'AG',
                    'vendor_name': instance.name,
                    'contact_person': instance.name,
                    'email': instance.email,
                    'phone': instance.phone,
                    'preferred_payment_method': instance.preferred_payment_method,
                    'is_active': instance.status == 'A'
                }
            )
            
            if vendor_created:
                logger.info(f"Created vendor record {vendor.vendor_code} for agent {instance.name}")
                
        except Exception as e:
            logger.error(f"Failed to create vendor for agent {instance.name}: {str(e)}")
