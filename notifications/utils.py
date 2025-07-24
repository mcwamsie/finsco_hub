from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from typing import List, Dict, Any
import logging

from .services import NotificationService
from .models import Notification, NotificationType

User = get_user_model()
logger = logging.getLogger(__name__)


def cleanup_old_notifications(days: int = 30) -> int:
    """
    Delete notifications older than specified days
    Use the cleanup_notifications management command instead
    
    Args:
        days: Number of days to keep notifications
        
    Returns:
        Number of notifications deleted
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        count, _ = Notification.objects.filter(created_at__lt=cutoff_date).delete()
        logger.info(f"Cleaned up {count} old notifications (older than {days} days)")
        return count
    except Exception as e:
        logger.error(f"Error cleaning up old notifications: {str(e)}")
        return 0


def get_notification_stats() -> Dict[str, Any]:
    """
    Get notification statistics
    
    Returns:
        Dictionary with notification statistics
    """
    try:
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(is_read=False).count()
        read_notifications = total_notifications - unread_notifications
        
        # Stats by type
        type_stats = {}
        for notif_type in NotificationType.objects.all():
            type_count = Notification.objects.filter(notification_type=notif_type).count()
            type_stats[notif_type.name] = type_count
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_count = Notification.objects.filter(created_at__gte=week_ago).count()
        
        return {
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'read_notifications': read_notifications,
            'read_percentage': (read_notifications / total_notifications * 100) if total_notifications > 0 else 0,
            'recent_notifications_7_days': recent_count,
            'notifications_by_type': type_stats,
            'active_notification_types': NotificationType.objects.filter(is_active=True).count(),
            'total_notification_types': NotificationType.objects.count(),
        }
    except Exception as e:
        logger.error(f"Error getting notification stats: {str(e)}")
        return {}


def get_user_notification_summary(user: User) -> Dict[str, Any]:
    """
    Get notification summary for a specific user
    
    Args:
        user: User to get summary for
        
    Returns:
        Dictionary with user notification summary
    """
    try:
        user_notifications = Notification.objects.filter(user=user)
        total = user_notifications.count()
        unread = user_notifications.filter(is_read=False).count()
        
        # Recent activity
        week_ago = timezone.now() - timedelta(days=7)
        recent = user_notifications.filter(created_at__gte=week_ago).count()
        
        # Most recent notification
        latest = user_notifications.order_by('-created_at').first()
        
        return {
            'user': user.username,
            'total_notifications': total,
            'unread_notifications': unread,
            'read_notifications': total - unread,
            'recent_notifications_7_days': recent,
            'latest_notification': {
                'title': latest.title if latest else None,
                'created_at': latest.created_at if latest else None,
                'is_read': latest.is_read if latest else None,
            } if latest else None,
        }
    except Exception as e:
        logger.error(f"Error getting user notification summary: {str(e)}")
        return {}


def create_system_notification(title: str, message: str, priority: str = 'MEDIUM') -> List[Notification]:
    """
    Create a system notification for all active users
    
    Args:
        title: Notification title
        message: Notification message
        priority: Notification priority (LOW, MEDIUM, HIGH, URGENT)
        
    Returns:
        List of created notifications
    """
    try:
        # Get or create system notification type
        notif_type, created = NotificationType.objects.get_or_create(
            name='SYSTEM_ANNOUNCEMENT',
            defaults={
                'description': 'System-wide announcements',
                'category': 'SYSTEM',
                'priority': priority
            }
        )
        
        if not created and notif_type.priority != priority:
            notif_type.priority = priority
            notif_type.save()
        
        # Send to all active users
        users = User.objects.filter(is_active=True)
        notifications = NotificationService.send_bulk_notifications(
            users=list(users),
            notification_type='SYSTEM_ANNOUNCEMENT',
            title=title,
            message=message
        )
        
        logger.info(f"Created system notification for {len(notifications)} users")
        return notifications
        
    except Exception as e:
        logger.error(f"Error creating system notification: {str(e)}")
        return []


def create_security_alert(title: str, message: str, target_users: List[User] = None) -> List[Notification]:
    """
    Create a security alert notification
    
    Args:
        title: Alert title
        message: Alert message
        target_users: Specific users to alert (defaults to all staff)
        
    Returns:
        List of created notifications
    """
    try:
        # Get or create security alert type
        notif_type, created = NotificationType.objects.get_or_create(
            name='SECURITY_ALERT',
            defaults={
                'description': 'Security alerts and warnings',
                'category': 'SECURITY',
                'priority': 'URGENT'
            }
        )
        
        # Default to staff users if no specific users provided
        if target_users is None:
            target_users = list(User.objects.filter(is_active=True, is_staff=True))
        
        notifications = NotificationService.send_bulk_notifications(
            users=target_users,
            notification_type='SECURITY_ALERT',
            title=title,
            message=message
        )
        
        logger.info(f"Created security alert for {len(notifications)} users")
        return notifications
        
    except Exception as e:
        logger.error(f"Error creating security alert: {str(e)}")
        return []


def send_welcome_notification(user: User) -> Notification:
    """
    Send welcome notification to new user
    
    Args:
        user: New user to welcome
        
    Returns:
        Created notification
    """
    try:
        title = f"Welcome to FISCO Hub, {user.first_name or user.username}!"
        message = (
            "Welcome to FISCO Hub! We're excited to have you on board. "
            "You can manage your notification preferences in your account settings."
        )
        
        return NotificationService.create_notification(
            user=user,
            notification_type='WELCOME',
            title=title,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error sending welcome notification: {str(e)}")
        raise


# Convenience functions for quick access (maintained for backward compatibility)
def system_announce(title: str, message: str, priority: str = 'MEDIUM') -> List[Notification]:
    """Quick function to create system announcement"""
    return create_system_notification(title, message, priority)


def security_alert(title: str, message: str, target_users: List[User] = None) -> List[Notification]:
    """Quick function to create security alert"""
    return create_security_alert(title, message, target_users)


def welcome_user(user: User) -> Notification:
    """Quick function to send welcome notification"""
    return send_welcome_notification(user)