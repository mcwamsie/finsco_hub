from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import Notification, NotificationType
from .services import NotificationService

User = get_user_model()


def create_notification(
    recipient, notification_type_name, title, message,
    content_object=None, send_immediately=True
):
    """
    Helper function to create notifications programmatically.
    
    Args:
        recipient: User instance
        notification_type_name: String name of the notification type
        title: Notification title
        message: Notification message
        content_object: Optional related object
        send_immediately: Whether to send the notification immediately
    """
    try:
        notification_type = NotificationType.objects.get(
            name=notification_type_name, is_active=True
        )
    except NotificationType.DoesNotExist:
        # Create a default notification type if it doesn't exist
        notification_type = NotificationType.objects.create(
            name=notification_type_name,
            description=f"Auto-created type for {notification_type_name}",
            category='SYSTEM',
            priority='MEDIUM'
        )
    
    # Use the NotificationService to create and send the notification
    return NotificationService.create_notification(
        user=recipient,
        notification_type=notification_type_name,
        title=title,
        message=message,
        content_object=content_object,
        send_immediately=send_immediately
    )


# Example signal receivers for common events
@receiver(user_logged_in)
def notify_user_login(sender, request, user, **kwargs):
    """Send notification when user logs in (optional)."""
    # Uncomment if you want login notifications
    # create_notification(
    #     recipient=user,
    #     notification_type_name='user_login',
    #     title='Login Successful',
    #     message=f'You have successfully logged in from {request.META.get("REMOTE_ADDR", "unknown IP")}.',
    # )
    pass


# You can add more signal receivers here for specific models
# Example for a hypothetical Order model:
# @receiver(post_save, sender=Order)
# def notify_order_created(sender, instance, created, **kwargs):
#     if created:
#         create_notification(
#             recipient=instance.user,
#             notification_type_name='order_created',
#             title='Order Confirmation',
#             message=f'Your order #{instance.id} has been created successfully.',
#             content_object=instance
#         )