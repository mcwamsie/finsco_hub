from celery import shared_task
from django.db import models
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_daily_sms_reports():
    """Send daily SMS usage reports"""
    try:
        from .models import SMSMessage
        from configurations.utils.notification_service import NotificationService

        # Get yesterday's SMS stats
        yesterday = timezone.now().date() - timedelta(days=1)

        stats = SMSMessage.objects.filter(
            created_at__date=yesterday
        ).aggregate(
            total=models.Count('id'),
            sent=models.Count('id', filter=models.Q(status='sent')),
            failed=models.Count('id', filter=models.Q(status='failed')),
            cost=models.Sum('cost')
        )

        # Send report to administrators
        notification_service = NotificationService()
        message = f"SMS Report {yesterday}: Sent: {stats['sent']}, Failed: {stats['failed']}, Cost: ${stats['cost'] or 0}"

        # Send to admin users
        from authentication.models import User
        admins = User.objects.filter(type='A', is_active=True)

        for admin in admins:
            notification_service.send_sms_notification(
                phone=admin.get_notification_phone(),
                message=message,
                message_type='notification'
            )

        logger.info(f"Daily SMS report sent: {message}")

    except Exception as e:
        logger.error(f"Failed to send daily SMS report: {str(e)}")


@shared_task
def cleanup_old_gateway_requests():
    """Clean up old gateway request records"""
    try:
        from .models import PaymentGatewayRequest, SMSMessage

        # Delete records older than 90 days
        cutoff_date = timezone.now() - timedelta(days=90)

        payment_deleted = PaymentGatewayRequest.objects.filter(
            request_timestamp__lt=cutoff_date
        ).delete()[0]

        sms_deleted = SMSMessage.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]

        logger.info(f"Cleaned up {payment_deleted} payment requests and {sms_deleted} SMS messages")

    except Exception as e:
        logger.error(f"Failed to cleanup old records: {str(e)}")


@shared_task
def refresh_expiring_payment_tokens():
    """Refresh payment gateway tokens that expire soon"""
    try:
        from .models import PaymentGatewayToken
        from configurations.utils.payment_service import PaymentGatewayService

        # Find tokens expiring in next hour
        expiring_soon = PaymentGatewayToken.objects.filter(
            expires_at__lte=timezone.now() + timedelta(hours=1),
            is_active=True
        )

        for token_info in expiring_soon:
            try:
                service = PaymentGatewayService(token_info.gateway)
                new_token = service.refresh_token()

                if new_token:
                    logger.info(f"Refreshed token for {token_info.gateway.name}")
                else:
                    logger.warning(f"Failed to refresh token for {token_info.gateway.name}")

            except Exception as e:
                logger.error(f"Token refresh error for {token_info.gateway.name}: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to refresh expiring tokens: {str(e)}")