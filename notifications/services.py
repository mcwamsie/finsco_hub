import logging
from typing import List, Dict, Any

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from authentication.models import User
from .models import Notification, NotificationType, NotificationLog

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service class for handling notification creation, sending, and management
    Integrates with User model's extensive notification preferences
    """

    @staticmethod
    def create_notification(user: User, notification_type: str, title: str, message: str, content_object=None, send_immediately: bool = True, priority: str = 'NORMAL') -> Notification:
        """
        Create a new notification for a user
        
        Args:
            user: The recipient user
            notification_type: String name of the notification type (must match User model fields)
            title: Notification title
            message: Notification message
            content_object: Optional related object
            send_immediately: Whether to send the notification immediately
            priority: Notification priority
            
        Returns:
            Created Notification instance
        """
        try:
            # Get or create notification type
            notif_type, created = NotificationType.objects.get_or_create(
                name=notification_type,
                defaults={
                    'description': f'Auto-created type: {notification_type}',
                    'category': NotificationService._get_category_for_type(notification_type),
                    'priority': priority
                }
            )

            # Create notification
            notification = Notification.objects.create(
                user=user,
                notification_type=notif_type,
                title=title,
                message=message,
                content_object=content_object
            )

            if send_immediately:
                NotificationService.send_notification(notification)

            logger.info(f"Created notification {notification.id} for user {user.username}")
            return notification

        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            raise

    @staticmethod
    def send_notification(notification: Notification) -> Dict[str, bool]:
        """
        Send notification through enabled channels based on User model preferences
        
        Args:
            notification: Notification instance to send
            
        Returns:
            Dictionary with channel send results
        """
        results = {
            'email': False,
            'sms': False,
            'push': False,
            'in_app': True  # In-app is always successful as it's just stored in DB
        }

        try:
            user = notification.user
            notification_type = notification.notification_type.name

            # Check if user can receive this notification type
            if not user.can_receive_notification(notification_type):
                logger.info(f"User {user.username} has disabled {notification_type} notifications")
                return results

            # Get active channels for this notification type
            active_channels = user.get_active_notification_channels(notification_type)

            # Send via each active channel
            for channel in active_channels:
                if channel == 'email':
                    results['email'] = NotificationService._send_email(notification)
                    notification.email_sent = results['email']
                elif channel == 'sms':
                    results['sms'] = NotificationService._send_sms(notification)
                    notification.sms_sent = results['sms']
                elif channel == 'push':
                    results['push'] = NotificationService._send_push(notification)
                    notification.push_sent = results['push']

            notification.save(update_fields=['email_sent', 'sms_sent', 'push_sent'])

            logger.info(f"Sent notification {notification.id} via channels: {results}")
            return results

        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {str(e)}")
            return results

    @staticmethod
    def send_bulk_notifications(
            users: List[User],
            notification_type: str,
            title: str,
            message: str,
            content_object=None,
            priority: str = 'NORMAL'
    ) -> List[Notification]:
        """
        Send notifications to multiple users
        
        Args:
            users: List of recipient users
            notification_type: String name of the notification type
            title: Notification title
            message: Notification message
            content_object: Optional related object
            priority: Notification priority
            
        Returns:
            List of created Notification instances
        """
        notifications = []

        try:
            with transaction.atomic():
                for user in users:
                    # Only create notification if user can receive it
                    if user.can_receive_notification(notification_type):
                        notification = NotificationService.create_notification(
                            user=user,
                            notification_type=notification_type,
                            title=title,
                            message=message,
                            content_object=content_object,
                            send_immediately=False,
                            priority=priority
                        )
                        notifications.append(notification)

                # Send all notifications
                for notification in notifications:
                    NotificationService.send_notification(notification)

            logger.info(f"Sent bulk notifications to {len(notifications)} users (filtered from {len(users)})")
            return notifications

        except Exception as e:
            logger.error(f"Error sending bulk notifications: {str(e)}")
            raise

    @staticmethod
    def send_user_specific_notification(
            user: User,
            activity_type: str,
            title: str,
            message: str,
            content_object=None,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Send notification using User model's enhanced notification system
        
        Args:
            user: User object
            activity_type: Type of activity (e.g., 'claim_approved')
            title: Notification title
            message: Notification message
            content_object: Optional related object
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with send results and details
        """
        try:
            # Check if user can receive this notification
            if not user.can_receive_notification(activity_type):
                return {
                    'sent': False,
                    'reason': 'User disabled this notification type',
                    'notification': None
                }

            # Get active channels
            channels = user.get_active_notification_channels(activity_type)

            if not channels:
                return {
                    'sent': False,
                    'reason': 'No active notification channels',
                    'notification': None
                }

            # Create notification
            notification = NotificationService.create_notification(
                user=user,
                notification_type=activity_type,
                title=title,
                message=message,
                content_object=content_object,
                send_immediately=False,
                priority=kwargs.get('priority', 'NORMAL')
            )

            # Send via active channels
            send_results = NotificationService.send_notification(notification)

            return {
                'sent': True,
                'channels': channels,
                'results': send_results,
                'notification': notification
            }

        except Exception as e:
            logger.error(f"Error sending user-specific notification: {str(e)}")
            return {
                'sent': False,
                'reason': f'Error: {str(e)}',
                'notification': None
            }

    @staticmethod
    def mark_as_read(notification_id: int, user: User) -> bool:
        """
        Mark a notification as read
        
        Args:
            notification_id: ID of the notification
            user: User who is marking it as read
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found for user {user.username}")
            return False
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False

    @staticmethod
    def mark_all_as_read(user: User) -> int:
        """
        Mark all unread notifications as read for a user
        
        Args:
            user: User whose notifications to mark as read
            
        Returns:
            Number of notifications marked as read
        """
        try:
            unread_notifications = Notification.objects.filter(user=user, is_read=False)
            count = unread_notifications.count()

            unread_notifications.update(
                is_read=True,
                read_at=timezone.now()
            )

            logger.info(f"Marked {count} notifications as read for user {user.username}")
            return count

        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return 0

    @staticmethod
    def get_unread_count(user: User) -> int:
        """
        Get count of unread notifications for a user
        
        Args:
            user: User to get count for
            
        Returns:
            Number of unread notifications
        """
        try:
            return Notification.objects.filter(user=user, is_read=False).count()
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return 0

    @staticmethod
    def get_recent_notifications(user: User, limit: int = 10) -> List[Notification]:
        """
        Get recent notifications for a user
        
        Args:
            user: User to get notifications for
            limit: Maximum number of notifications to return
            
        Returns:
            List of recent Notification instances
        """
        try:
            return list(Notification.objects.filter(user=user)[:limit])
        except Exception as e:
            logger.error(f"Error getting recent notifications: {str(e)}")
            return []

    @staticmethod
    def _send_email(notification: Notification) -> bool:
        """Send email notification"""
        try:
            user = notification.user

            # Create notification log
            log = NotificationLog.objects.create(
                notification=notification,
                channel='email',
                status='pending'
            )

            try:
                send_mail(
                    subject=notification.title,
                    message=notification.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )

                # Update log
                log.status = 'sent'
                log.sent_at = timezone.now()
                log.save()

                notification.update_delivery_status('email', True)
                return True

            except Exception as e:
                # Update log with error
                log.status = 'failed'
                log.error_message = str(e)
                log.save()

                notification.update_delivery_status('email', False, str(e))
                logger.error(f"Failed to send email for notification {notification.id}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error in email sending process: {str(e)}")
            return False

    @staticmethod
    def _send_sms(notification: Notification) -> bool:
        """Send SMS notification"""
        try:
            user = notification.user
            phone = user.get_notification_phone()

            if not phone:
                logger.warning(f"No phone number for SMS notification {notification.id}")
                return False

            # Create notification log
            log = NotificationLog.objects.create(
                notification=notification,
                channel='sms',
                status='pending'
            )

            try:
                # TODO: Implement actual SMS sending (Twilio, etc.)
                # For now, just log the attempt
                logger.info(f"SMS would be sent to {phone}: {notification.message}")

                # Update log
                log.status = 'sent'
                log.sent_at = timezone.now()
                log.save()

                notification.update_delivery_status('sms', True)
                return True

            except Exception as e:
                # Update log with error
                log.status = 'failed'
                log.error_message = str(e)
                log.save()

                notification.update_delivery_status('sms', False, str(e))
                logger.error(f"Failed to send SMS for notification {notification.id}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error in SMS sending process: {str(e)}")
            return False

    @staticmethod
    def _send_push(notification: Notification) -> bool:
        """Send push notification"""
        try:
            # Create notification log
            log = NotificationLog.objects.create(
                notification=notification,
                channel='push',
                status='pending'
            )

            try:
                # TODO: Implement actual push notification sending
                # For now, just log the attempt
                logger.info(f"Push notification would be sent: {notification.title}")

                # Update log
                log.status = 'sent'
                log.sent_at = timezone.now()
                log.save()

                notification.update_delivery_status('push', True)
                return True

            except Exception as e:
                # Update log with error
                log.status = 'failed'
                log.error_message = str(e)
                log.save()

                notification.update_delivery_status('push', False, str(e))
                logger.error(f"Failed to send push notification {notification.id}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error in push notification sending process: {str(e)}")
            return False

    @staticmethod
    def _get_category_for_type(notification_type: str) -> str:
        """Determine category based on notification type name"""
        category_mappings = {
            'member_': 'MEMBER',
            'beneficiary_': 'MEMBER',
            'claim_': 'CLAIMS',
            'service_request_': 'AUTHORIZATION',
            'authorization_': 'AUTHORIZATION',
            'topup_': 'ACCOUNT',
            'balance_': 'ACCOUNT',
            'account_': 'ACCOUNT',
            'limit_': 'ACCOUNT',
            'provider_': 'PROVIDER',
            'commission_': 'COMMISSION',
            'kyc_': 'KYC',
            'document_': 'KYC',
            'login_': 'SECURITY',
            'password_': 'SECURITY',
            'failed_': 'SECURITY',
            'system_': 'SYSTEM',
            'feature_': 'SYSTEM',
            'policy_': 'SYSTEM',
            'promotion': 'MARKETING',
            'newsletter': 'MARKETING',
            'survey': 'MARKETING',
            'health_': 'MARKETING',
            'emergency_': 'EMERGENCY',
            'fraud_': 'EMERGENCY',
        }

        for prefix, category in category_mappings.items():
            if notification_type.startswith(prefix):
                return category

        return 'GENERAL'
