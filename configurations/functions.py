import logging

from django.core.mail import send_mail
from django.utils import timezone

from accounting.models import MemberTransaction
from configurations.models import Agent, AgentCommission
from fisco_hub_8d import settings
from membership.models import TopUp
from services.models import Claim

logger = logging.getLogger(__name__)


def send_agent_bonus_notification(agent: Agent, commission: AgentCommission):
    """Send bonus notification to agent via SMS and email"""
    from configurations.utils.notification_service import NotificationService

    notification_service = NotificationService()

    subject = f"Commission Bonus Awarded - {commission.commission_number}"
    message = f"Congratulations! You've earned ${commission.commission_amount} bonus for {commission.commission_term.name}"

    # Send via preferred method
    result = notification_service.send_notification(
        recipient=agent,
        subject=subject,
        message=message,
        notification_type='notification'
    )

    logger.info(
        f"Sent bonus notification to agent {agent.name}: Email={result['email']['sent']}, SMS={result['sms']['sent']}")


def send_compliance_notification(provider, issues):
    """Send compliance notification to service provider"""
    try:
        subject = f"Compliance Issues - {provider.account_no}"
        message = f"""
        Dear {provider.name},

        We have identified the following compliance issues with your account:

        {chr(10).join([f"- {issue}" for issue in issues])}

        Please address these issues immediately to avoid payment withholding.

        Best regards,
        Medical Aid Team
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[provider.email],
            fail_silently=True
        )

    except Exception as e:
        logger.error(f"Failed to send compliance notification: {str(e)}")


def send_document_expiry_warning(document):
    """Send document expiry warning via SMS and email"""
    from configurations.utils.notification_service import NotificationService

    notification_service = NotificationService()

    days_remaining = (document.expiry_date - timezone.now().date()).days

    subject = f"Document Expiry Warning - {document.document_type.name}"
    message = f"URGENT: Your {document.document_type.name} expires in {days_remaining} days ({document.expiry_date}). Please renew immediately."

    result = notification_service.send_notification(
        recipient=document.service_provider,
        subject=subject,
        message=message,
        notification_type='alert',
        priority='urgent'
    )

def send_topup_confirmation(topup: TopUp):
    """Send top-up confirmation via SMS and email"""
    from configurations.utils.notification_service import NotificationService

    notification_service = NotificationService()

    subject = f"Top-up Confirmation - {topup.top_up_number}"
    message = f"Top-up successful! Amount: ${topup.net_amount}. New balance: ${topup.account.available_balance}. Ref: {topup.top_up_number}"

    for signatories in topup.member.signatories.all():
        result = notification_service.send_notification(
            recipient=signatories,
            subject=subject,
            message=message,
            notification_type='notification'
        )

    logger.info(f"Sent top-up confirmation to member {topup.member.membership_number}")


def send_claim_approval_notification(claim: Claim):
    """Send claim approval notification via SMS and email"""
    from configurations.utils.notification_service import NotificationService

    notification_service = NotificationService()

    subject = f"Claim Approved - {claim.transaction_number}"
    message = f"Your claim {claim.transaction_number} for ${claim.accepted_amount} has been approved. Provider: {claim.provider.name}"

    result = notification_service.send_notification(
        recipient=claim.beneficiary.member,
        subject=subject,
        message=message,
        notification_type='notification'
    )


def send_authorization_notification(service_request):
    """Send authorization notification via SMS and email"""
    from configurations.utils.notification_service import NotificationService

    notification_service = NotificationService()

    subject = f"Authorization Approved - {service_request.authorization_code}"
    message = f"Service authorized! Code: {service_request.authorization_code}. Amount: ${service_request.approved_amount}. Valid until: {service_request.expiry_date}"

    result = notification_service.send_notification(
        recipient=service_request.beneficiary.member,
        subject=subject,
        message=message,
        notification_type='notification'
    )


def send_kyc_completion_notification(member):
    """Send KYC completion notification"""
    try:
        subject = f"KYC Verification Complete - {member.membership_number}"
        message = f"""
        Dear {member.name},

        Your KYC verification has been completed successfully.

        Membership Number: {member.membership_number}
        Verification Date: {member.kyc_verified_at.strftime('%Y-%m-%d')}

        You can now access all services available under your membership.

        Best regards,
        Medical Aid Team
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member.email],
            fail_silently=True
        )

    except Exception as e:
        logger.error(f"Failed to send KYC completion notification: {str(e)}")


def reserve_funds_for_authorization(service_request, amount):
    """Reserve funds in member account for authorization"""
    try:
        member_account = service_request.beneficiary.member.accounts.filter(
            currency=service_request.beneficiary.member.currency
        ).first()

        if member_account and member_account.available_balance >= amount:
            # Create reserve transaction
            MemberTransaction.objects.create(
                account=member_account,
                transaction_type='R',
                amount_debited=amount,
                balance=member_account.balance,
                available_balance=member_account.available_balance - amount,
                description=f'Reserve for authorization: {service_request.authorization_code}',
                reference=service_request.authorization_code,
                service_request=service_request,
                status='C'
            )

            logger.info(f"Reserved ${amount} for authorization {service_request.authorization_code}")

    except Exception as e:
        logger.error(f"Failed to reserve funds: {str(e)}")

