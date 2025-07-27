from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from typing import Dict, List, Optional
import logging

from configurations.utils.sms_service import SMSService

logger = logging.getLogger(__name__)


class NotificationService:
    """Unified notification service for email and SMS"""

    def __init__(self):
        self.sms_service = SMSService()

    def send_notification(self, recipient, subject: str, message: str, notification_type: str = 'notification', template: str = None, context: Dict = None, priority: str = 'normal') -> Dict:
        """Send notification via preferred method"""

        results = {
            'email': {'sent': False, 'error': None},
            'sms': {'sent': False, 'error': None}
        }

        # Determine recipient type and get communication preferences
        if hasattr(recipient, 'preferred_notification_method'):
            user = recipient
        elif hasattr(recipient, 'signatories') and recipient.signatories.exists():
            user = recipient.signatories.first()
        else:
            # Default user with email/SMS preferences
            user = None

        # Send email if preferred
        if user and user.preferred_notification_method in ['email', 'both']:
            if user.receive_email_notifications:
                email_result = self.send_email_notification(
                    user.email, subject, message, template, context
                )
                results['email'] = email_result

        # Send SMS if preferred
        if user and user.preferred_notification_method in ['sms', 'both']:
            if user.can_receive_sms(notification_type) and not user.is_in_quiet_hours():
                phone = user.get_notification_phone()
                if phone:
                    sms_result = self.send_sms_notification(
                        phone, message, notification_type, priority
                    )
                    results['sms'] = sms_result

        return results

    @staticmethod
    def send_email_notification(self, email: str, subject: str, message: str, template: str = None, context: Dict = None) -> Dict:
        """Send email notification"""

        try:
            if template and context:
                html_message = render_to_string(template, context)
                plain_message = strip_tags(html_message)
            else:
                html_message = None
                plain_message = message

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False
            )

            return {'sent': True, 'error': None}

        except Exception as e:
            logger.error(f"Email notification failed: {str(e)}")
            return {'sent': False, 'error': str(e)}

    def send_sms_notification(self, phone: str, message: str, message_type: str = 'notification', priority: str = 'normal') -> Dict:
        """Send SMS notification"""

        try:
            # Truncate message if too long
            gateway = SMSService.get_primary_gateway()
            if gateway:
                max_length = gateway.max_message_length
                if len(message) > max_length:
                    message = message[:max_length - 3] + '...'

            result = self.sms_service.send_sms(
                recipient=phone,
                message=message,
                message_type=message_type,
                priority=priority
            )

            return {
                'sent': result['success'],
                'error': result.get('error'),
                'message_id': result.get('message_id')
            }

        except Exception as e:
            logger.error(f"SMS notification failed: {str(e)}")
            return {'sent': False, 'error': str(e)}

    def send_bulk_notification(self, recipients: List, subject: str, message: str, notification_type: str = 'notification') -> Dict:
        """Send notification to multiple recipients"""

        results = {
            'total': len(recipients),
            'email_sent': 0,
            'sms_sent': 0,
            'failed': 0,
            'details': []
        }

        for recipient in recipients:
            try:
                result = self.send_notification(
                    recipient, subject, message, notification_type
                )

                detail = {
                    'recipient': str(recipient),
                    'email_sent': result['email']['sent'],
                    'sms_sent': result['sms']['sent'],
                    'errors': []
                }

                if result['email']['sent']:
                    results['email_sent'] += 1
                elif result['email']['error']:
                    detail['errors'].append(f"Email: {result['email']['error']}")

                if result['sms']['sent']:
                    results['sms_sent'] += 1
                elif result['sms']['error']:
                    detail['errors'].append(f"SMS: {result['sms']['error']}")

                if not (result['email']['sent'] or result['sms']['sent']):
                    results['failed'] += 1

                results['details'].append(detail)

            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'recipient': str(recipient),
                    'email_sent': False,
                    'sms_sent': False,
                    'errors': [str(e)]
                })

        return results