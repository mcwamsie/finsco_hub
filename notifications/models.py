from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationType(models.Model):
    """
    Predefined notification types that map to User model notification preferences
    """
    CATEGORIES = [
        ('MEMBER', 'Member Activities'),
        ('CLAIMS', 'Claims'),
        ('AUTHORIZATION', 'Service Requests & Authorization'),
        ('ACCOUNT', 'Account & Financial'),
        ('PROVIDER', 'Provider Activities'),
        ('COMMISSION', 'Agent Commission'),
        ('KYC', 'KYC & Compliance'),
        ('SECURITY', 'Security'),
        ('SYSTEM', 'System'),
        ('MARKETING', 'Marketing & Promotional'),
        ('EMERGENCY', 'Emergency'),
        ('GENERAL', 'General'),
    ]
    
    PRIORITIES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    name = models.CharField(max_length=100, unique=True, help_text="Must match User model notification field names")
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='GENERAL')
    priority = models.CharField(max_length=10, choices=PRIORITIES, default='NORMAL')
    
    # Default channel settings (can be overridden by user preferences)
    default_email_enabled = models.BooleanField(default=True)
    default_push_enabled = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = "Notification Type"
        verbose_name_plural = "Notification Types"
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"
    
    def get_user_preference_field(self):
        """Get the corresponding User model field name for this notification type"""
        return f"notify_{self.name}"
    
    def get_user_sms_preference_field(self):
        """Get the corresponding User model SMS field name for this notification type"""
        return f"notify_{self.name}_sms"
    
    def get_user_email_preference_field(self):
        """Get the corresponding User model email field name for this notification type"""
        return f"notify_{self.name}_email"


class Notification(models.Model):
    """Individual notification instances"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Generic foreign key for related object
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Status tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery tracking
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    push_sent = models.BooleanField(default=False)
    
    # Delivery status
    email_delivered = models.BooleanField(default=False)
    sms_delivered = models.BooleanField(default=False)
    push_delivered = models.BooleanField(default=False)
    
    # Error tracking
    email_error = models.TextField(blank=True)
    sms_error = models.TextField(blank=True)
    push_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
            logger.info(f"Notification {self.id} marked as read by {self.user.username}")
    
    def can_send_via_channel(self, channel: str) -> bool:
        """
        Check if notification can be sent via specified channel based on user preferences
        
        Args:
            channel: 'email', 'sms', or 'push'
            
        Returns:
            bool: Whether notification can be sent via this channel
        """
        try:
            # Check if user can receive this notification type via the specified channel
            return self.user.can_receive_notification(self.notification_type.name, channel)
        except Exception as e:
            logger.error(f"Error checking channel permission for notification {self.id}: {str(e)}")
            return False
    
    def get_delivery_status(self) -> dict:
        """Get comprehensive delivery status"""
        return {
            'email': {
                'sent': self.email_sent,
                'delivered': self.email_delivered,
                'error': self.email_error
            },
            'sms': {
                'sent': self.sms_sent,
                'delivered': self.sms_delivered,
                'error': self.sms_error
            },
            'push': {
                'sent': self.push_sent,
                'delivered': self.push_delivered,
                'error': self.push_error
            }
        }
    
    def update_delivery_status(self, channel: str, delivered: bool, error: str = ''):
        """Update delivery status for a specific channel"""
        if channel == 'email':
            self.email_delivered = delivered
            self.email_error = error
        elif channel == 'sms':
            self.sms_delivered = delivered
            self.sms_error = error
        elif channel == 'push':
            self.push_delivered = delivered
            self.push_error = error
        
        self.save(update_fields=[f'{channel}_delivered', f'{channel}_error'])


class NotificationLog(models.Model):
    """
    Log of all notification attempts for analytics and debugging
    """
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    channel = models.CharField(max_length=10, choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push'),
    ])
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Provider information
    provider = models.CharField(max_length=50, blank=True)  # e.g., 'sendgrid', 'twilio'
    provider_message_id = models.CharField(max_length=255, blank=True)
    
    # Timing
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Error details
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification', 'channel']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification.title} - {self.channel} - {self.status}"
