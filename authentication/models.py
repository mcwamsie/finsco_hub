# authentication/models.py
import logging

from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
# from simple_history.models import HistoricalRecords
import uuid


logger = logging.getLogger(__name__)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic Information
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    # Additional Personal Info
    national_id_no = models.CharField(
        max_length=150,
        help_text="format:XX-XXXXXX-A-XX",
        blank=True,
        null=True,
        verbose_name="National ID Number"
    )
    profile_photo = models.ImageField(
        blank=True,
        null=True,
        upload_to="users/profile-photos",
        verbose_name="Profile Photo"
    )

    # Contact Information
    phone = PhoneNumberField(max_length=20, verbose_name="Phone Number")
    alternative_phone = PhoneNumberField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Alternative Phone Number"
    )

    # Global Communication Preferences
    NOTIFICATION_METHODS = [
        ('email', 'Email Only'),
        ('sms', 'SMS Only'),
        ('both', 'Email and SMS'),
        ('none', 'No Notifications'),
    ]
    preferred_notification_method = models.CharField(
        max_length=10,
        choices=NOTIFICATION_METHODS,
        default='both',
        verbose_name="Preferred Notification Method"
    )

    # Global SMS/Email Toggle
    receive_sms_notifications = models.BooleanField(default=True, verbose_name="Receive SMS Notifications")
    receive_email_notifications = models.BooleanField(default=True, verbose_name="Receive Email Notifications")

    # Language and Timezone
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sn', 'Shona'),
        ('nd', 'Ndebele'),
    ]
    preferred_language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='en',
        verbose_name="Preferred Language"
    )
    timezone = models.CharField(max_length=50, default='Africa/Harare', verbose_name="Timezone")

    # DND (Do Not Disturb) Settings
    sms_quiet_hours_start = models.TimeField(null=True, blank=True, verbose_name="SMS Quiet Hours Start")
    sms_quiet_hours_end = models.TimeField(null=True, blank=True, verbose_name="SMS Quiet Hours End")
    email_quiet_hours_start = models.TimeField(null=True, blank=True, verbose_name="Email Quiet Hours Start")
    email_quiet_hours_end = models.TimeField(null=True, blank=True, verbose_name="Email Quiet Hours End")

    # Essential Notification Categories (simplified)
    notify_applications = models.BooleanField(default=True, verbose_name="Member / Service Provider Notifications")
    notify_security_alerts = models.BooleanField(default=True, verbose_name="Security Alerts")
    notify_account_activities = models.BooleanField(default=True, verbose_name="Account Activities")
    notify_claims_updates = models.BooleanField(default=True, verbose_name="Claims Updates")
    notify_system_updates = models.BooleanField(default=True, verbose_name="System Updates")
    notify_marketing = models.BooleanField(default=False, verbose_name="Marketing & Promotions")

    # Account Balance Threshold
    low_balance_threshold = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=100.00,
        verbose_name="Low Balance Threshold"
    )

    # System Associations
    member = models.ForeignKey(
        'configurations.Member',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="signatories"
    )
    profile_id = models.UUIDField(blank=True, null=True, verbose_name="Profile ID")
    service_provider = models.ForeignKey(
        'configurations.ServiceProvider',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users"
    )
    agent = models.ForeignKey(
        'configurations.Agent',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users"
    )
    designation = models.CharField(max_length=255, default="Admin", verbose_name="Designation")

    # User Types
    USER_TYPES = [
        ("A", "Administrator"),
        ("M", "Member Admin"),
        ("S", "Service Provider Admin"),
        ("G", "Agent"),
        ("D", "Account Manager"),
    ]
    type = models.CharField(max_length=1, choices=USER_TYPES, default="A", verbose_name="User Type")

    # Many-to-Many Relationships
    members = models.ManyToManyField(
        'configurations.Member',
        blank=True,
        related_name="account_managers"
    )

    # Security Settings
    failed_login_attempts = models.PositiveIntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    force_password_change = models.BooleanField(default=False)

    # Login Tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_count = models.PositiveIntegerField(default=0)

    # Two-Factor Authentication
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)
    backup_codes = models.JSONField(default=list, blank=True)

    # history = HistoricalRecords()

    def can_receive_notification(self, notification_type: str, channel: str = 'both') -> bool:
        """
        Check if user can receive notification for specific type and channel
        
        Args:
            notification_type: The notification category (e.g., 'security', 'claims', 'account')
            channel: 'sms', 'email', or 'both'
        
        Returns:
            bool: Whether the user should receive this notification
        """
        # Check global notification settings first
        if not self.receive_sms_notifications and channel in ['sms', 'both']:
            return False
        if not self.receive_email_notifications and channel in ['email', 'both']:
            return False

        # Check if it's quiet hours
        if channel in ['sms', 'both'] and self.is_in_sms_quiet_hours():
            return False
        if channel in ['email', 'both'] and self.is_in_email_quiet_hours():
            return False

        # Check category-specific settings
        category_mapping = {
            'security': self.notify_security_alerts,
            'account': self.notify_account_activities,
            'claims': self.notify_claims_updates,
            'system': self.notify_system_updates,
            'marketing': self.notify_marketing,
        }
        
        # Extract category from notification_type
        for category, enabled in category_mapping.items():
            if category in notification_type.lower():
                return enabled
        
        # Default to enabled for unmapped types (like emergency alerts)
        return True

    def get_notification_phone(self):
        """Get the phone number for SMS notifications"""
        if self.receive_sms_notifications:
            return str(self.phone) if self.phone else None
        return None

    def is_in_sms_quiet_hours(self):
        """Check if current time is in user's SMS quiet hours"""
        if not (self.sms_quiet_hours_start and self.sms_quiet_hours_end):
            return False

        import pytz
        from datetime import datetime

        user_tz = pytz.timezone(self.timezone)
        current_time = datetime.now(user_tz).time()

        start = self.sms_quiet_hours_start
        end = self.sms_quiet_hours_end

        if start <= end:
            return start <= current_time <= end
        else:  # Crosses midnight
            return current_time >= start or current_time <= end

    def is_in_email_quiet_hours(self):
        """Check if current time is in user's email quiet hours"""
        if not (self.email_quiet_hours_start and self.email_quiet_hours_end):
            return False

        import pytz
        from datetime import datetime

        user_tz = pytz.timezone(self.timezone)
        current_time = datetime.now(user_tz).time()

        start = self.email_quiet_hours_start
        end = self.email_quiet_hours_end

        if start <= end:
            return start <= current_time <= end
        else:  # Crosses midnight
            return current_time >= start or current_time <= end

    def is_account_locked(self):
        """Check if account is locked due to failed login attempts"""
        if self.account_locked_until:
            from django.utils import timezone
            return timezone.now() < self.account_locked_until
        return False

    def get_active_notification_channels(self, notification_type: str):
        """Get active notification channels for a specific notification type"""
        channels = []

        if self.can_receive_notification(notification_type, 'sms'):
            channels.append('sms')

        if self.can_receive_notification(notification_type, 'email'):
            channels.append('email')

        return channels

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        if self.first_name and self.last_name:
            full_name = f'{self.first_name} {self.last_name}'
            return full_name.strip()
        else:
            return self.username

    @property
    def get_initials(self):
        return self.get_full_name()[0].upper()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def __str__(self):
        return self.username

    class Meta:
        ordering = ["first_name", "last_name"]
        verbose_name = "User"
        verbose_name_plural = "Users"


class NotificationPreference(models.Model):
    """
    Detailed notification preferences for specific activities
    This replaces the numerous individual notification fields in User model
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Notification Categories
    NOTIFICATION_CATEGORIES = [
        ('member_registration', 'Member Registration'),
        ('member_status_change', 'Member Status Change'),
        ('beneficiary_addition', 'Beneficiary Addition'),
        ('beneficiary_removal', 'Beneficiary Removal'),
        ('claim_submitted', 'Claim Submitted'),
        ('claim_approved', 'Claim Approved'),
        ('claim_declined', 'Claim Declined'),
        ('claim_paid', 'Claim Paid'),
        ('authorization_approved', 'Authorization Approved'),
        ('authorization_declined', 'Authorization Declined'),
        ('topup_successful', 'Top-up Successful'),
        ('topup_failed', 'Top-up Failed'),
        ('low_balance', 'Low Balance Alert'),
        ('account_locked', 'Account Locked'),
        ('password_changed', 'Password Changed'),
        ('kyc_verified', 'KYC Verified'),
        ('kyc_rejected', 'KYC Rejected'),
        ('system_maintenance', 'System Maintenance'),
        ('emergency_alert', 'Emergency Alert'),
        ('fraud_alert', 'Fraud Alert'),
    ]
    
    activity_type = models.CharField(max_length=50, choices=NOTIFICATION_CATEGORIES)
    enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'activity_type']
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"


# Helper functions for notification service integration
def get_user_notification_preferences(user: User, activity_type: str):
    """
    Get notification preferences for a user and activity type
    
    Returns:
        dict: Notification preferences including channels and settings
    """
    try:
        preference = NotificationPreference.objects.get(user=user, activity_type=activity_type)
        enabled = preference.enabled
        sms_enabled = preference.sms_enabled
        email_enabled = preference.email_enabled
    except NotificationPreference.DoesNotExist:
        # Default preferences based on activity type
        enabled = True
        sms_enabled = True
        email_enabled = True
    
    # Check global user preferences
    can_receive_sms = user.can_receive_notification(activity_type, 'sms') and sms_enabled
    can_receive_email = user.can_receive_notification(activity_type, 'email') and email_enabled
    
    return {
        'enabled': enabled,
        'can_receive_sms': can_receive_sms,
        'can_receive_email': can_receive_email,
        'channels': [ch for ch in ['sms', 'email'] if (ch == 'sms' and can_receive_sms) or (ch == 'email' and can_receive_email)],
        'in_quiet_hours': {
            'sms': user.is_in_sms_quiet_hours(),
            'email': user.is_in_email_quiet_hours()
        }
    }


def send_notification(user, activity_type, subject, message, **kwargs):
    """
    Send notification using the notification service with user preferences
    
    Args:
        user: User object
        activity_type: Type of activity (e.g., 'claim_approved')
        subject: Notification subject
        message: Notification message
        **kwargs: Additional parameters for notification service
    """
    from configurations.utils.notification_service import NotificationService
    
    # Get user preferences
    preferences = get_user_notification_preferences(user, activity_type)
    
    if not preferences['enabled'] or not preferences['channels']:
        return {'sent': False, 'reason': 'User disabled this notification or no active channels'}
    
    # Use the notification service
    notification_service = NotificationService()
    
    return notification_service.send_notification(
        recipient=user,
        subject=subject,
        message=message,
        notification_type=activity_type,
        template=kwargs.get('template'),
        context=kwargs.get('context'),
        priority=kwargs.get('priority', 'normal')
    )