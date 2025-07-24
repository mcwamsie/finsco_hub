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

    # =======================
    # MEMBER ACTIVITY NOTIFICATIONS
    # =======================

    # Member Registration & Management
    notify_member_registration = models.BooleanField(default=True, verbose_name="Member Registration")
    notify_member_registration_sms = models.BooleanField(default=True, verbose_name="Member Registration SMS")
    notify_member_registration_email = models.BooleanField(default=True, verbose_name="Member Registration Email")

    notify_member_status_change = models.BooleanField(default=True, verbose_name="Member Status Changes")
    notify_member_status_change_sms = models.BooleanField(default=True, verbose_name="Member Status Change SMS")
    notify_member_status_change_email = models.BooleanField(default=True, verbose_name="Member Status Change Email")

    notify_member_profile_update = models.BooleanField(default=False, verbose_name="Member Profile Updates")
    notify_member_profile_update_sms = models.BooleanField(default=False, verbose_name="Member Profile Update SMS")
    notify_member_profile_update_email = models.BooleanField(default=True, verbose_name="Member Profile Update Email")

    notify_beneficiary_addition = models.BooleanField(default=True, verbose_name="Beneficiary Addition")
    notify_beneficiary_addition_sms = models.BooleanField(default=True, verbose_name="Beneficiary Addition SMS")
    notify_beneficiary_addition_email = models.BooleanField(default=True, verbose_name="Beneficiary Addition Email")

    notify_beneficiary_removal = models.BooleanField(default=True, verbose_name="Beneficiary Removal")
    notify_beneficiary_removal_sms = models.BooleanField(default=True, verbose_name="Beneficiary Removal SMS")
    notify_beneficiary_removal_email = models.BooleanField(default=True, verbose_name="Beneficiary Removal Email")

    # =======================
    # CLAIMS NOTIFICATIONS
    # =======================

    # Claim Submission
    notify_claim_submitted = models.BooleanField(default=True, verbose_name="Claim Submitted")
    notify_claim_submitted_sms = models.BooleanField(default=True, verbose_name="Claim Submitted SMS")
    notify_claim_submitted_email = models.BooleanField(default=True, verbose_name="Claim Submitted Email")

    # Claim Processing
    notify_claim_under_review = models.BooleanField(default=True, verbose_name="Claim Under Review")
    notify_claim_under_review_sms = models.BooleanField(default=False, verbose_name="Claim Under Review SMS")
    notify_claim_under_review_email = models.BooleanField(default=True, verbose_name="Claim Under Review Email")

    notify_claim_approved = models.BooleanField(default=True, verbose_name="Claim Approved")
    notify_claim_approved_sms = models.BooleanField(default=True, verbose_name="Claim Approved SMS")
    notify_claim_approved_email = models.BooleanField(default=True, verbose_name="Claim Approved Email")

    notify_claim_declined = models.BooleanField(default=True, verbose_name="Claim Declined")
    notify_claim_declined_sms = models.BooleanField(default=True, verbose_name="Claim Declined SMS")
    notify_claim_declined_email = models.BooleanField(default=True, verbose_name="Claim Declined Email")

    notify_claim_modified = models.BooleanField(default=True, verbose_name="Claim Amount Modified")
    notify_claim_modified_sms = models.BooleanField(default=True, verbose_name="Claim Modified SMS")
    notify_claim_modified_email = models.BooleanField(default=True, verbose_name="Claim Modified Email")

    # Claim Payments
    notify_claim_paid = models.BooleanField(default=True, verbose_name="Claim Paid")
    notify_claim_paid_sms = models.BooleanField(default=True, verbose_name="Claim Paid SMS")
    notify_claim_paid_email = models.BooleanField(default=True, verbose_name="Claim Paid Email")

    notify_claim_payment_failed = models.BooleanField(default=True, verbose_name="Claim Payment Failed")
    notify_claim_payment_failed_sms = models.BooleanField(default=True, verbose_name="Claim Payment Failed SMS")
    notify_claim_payment_failed_email = models.BooleanField(default=True, verbose_name="Claim Payment Failed Email")

    # =======================
    # SERVICE REQUEST NOTIFICATIONS (Pre-Authorization)
    # =======================

    notify_service_request_submitted = models.BooleanField(default=True, verbose_name="Service Request Submitted")
    notify_service_request_submitted_sms = models.BooleanField(default=False,
                                                               verbose_name="Service Request Submitted SMS")
    notify_service_request_submitted_email = models.BooleanField(default=True,
                                                                 verbose_name="Service Request Submitted Email")

    notify_authorization_approved = models.BooleanField(default=True, verbose_name="Authorization Approved")
    notify_authorization_approved_sms = models.BooleanField(default=True, verbose_name="Authorization Approved SMS")
    notify_authorization_approved_email = models.BooleanField(default=True, verbose_name="Authorization Approved Email")

    notify_authorization_declined = models.BooleanField(default=True, verbose_name="Authorization Declined")
    notify_authorization_declined_sms = models.BooleanField(default=True, verbose_name="Authorization Declined SMS")
    notify_authorization_declined_email = models.BooleanField(default=True, verbose_name="Authorization Declined Email")

    notify_authorization_expired = models.BooleanField(default=True, verbose_name="Authorization Expired")
    notify_authorization_expired_sms = models.BooleanField(default=True, verbose_name="Authorization Expired SMS")
    notify_authorization_expired_email = models.BooleanField(default=False, verbose_name="Authorization Expired Email")

    notify_authorization_utilized = models.BooleanField(default=False, verbose_name="Authorization Utilized")
    notify_authorization_utilized_sms = models.BooleanField(default=False, verbose_name="Authorization Utilized SMS")
    notify_authorization_utilized_email = models.BooleanField(default=True, verbose_name="Authorization Utilized Email")

    # =======================
    # ACCOUNT & FINANCIAL NOTIFICATIONS
    # =======================

    # Top-up Activities
    notify_topup_initiated = models.BooleanField(default=True, verbose_name="Top-up Initiated")
    notify_topup_initiated_sms = models.BooleanField(default=True, verbose_name="Top-up Initiated SMS")
    notify_topup_initiated_email = models.BooleanField(default=False, verbose_name="Top-up Initiated Email")

    notify_topup_successful = models.BooleanField(default=True, verbose_name="Top-up Successful")
    notify_topup_successful_sms = models.BooleanField(default=True, verbose_name="Top-up Successful SMS")
    notify_topup_successful_email = models.BooleanField(default=True, verbose_name="Top-up Successful Email")

    notify_topup_failed = models.BooleanField(default=True, verbose_name="Top-up Failed")
    notify_topup_failed_sms = models.BooleanField(default=True, verbose_name="Top-up Failed SMS")
    notify_topup_failed_email = models.BooleanField(default=True, verbose_name="Top-up Failed Email")

    # Account Balance Alerts
    notify_low_balance = models.BooleanField(default=True, verbose_name="Low Balance Alert")
    notify_low_balance_sms = models.BooleanField(default=True, verbose_name="Low Balance Alert SMS")
    notify_low_balance_email = models.BooleanField(default=False, verbose_name="Low Balance Alert Email")
    low_balance_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=100.00,
                                                verbose_name="Low Balance Threshold")

    notify_negative_balance = models.BooleanField(default=True, verbose_name="Negative Balance Alert")
    notify_negative_balance_sms = models.BooleanField(default=True, verbose_name="Negative Balance Alert SMS")
    notify_negative_balance_email = models.BooleanField(default=True, verbose_name="Negative Balance Alert Email")

    notify_account_credited = models.BooleanField(default=True, verbose_name="Account Credited")
    notify_account_credited_sms = models.BooleanField(default=True, verbose_name="Account Credited SMS")
    notify_account_credited_email = models.BooleanField(default=False, verbose_name="Account Credited Email")

    notify_account_debited = models.BooleanField(default=False, verbose_name="Account Debited")
    notify_account_debited_sms = models.BooleanField(default=False, verbose_name="Account Debited SMS")
    notify_account_debited_email = models.BooleanField(default=True, verbose_name="Account Debited Email")

    # Monthly/Annual Limits
    notify_limit_warning = models.BooleanField(default=True, verbose_name="Limit Warning (80%)")
    notify_limit_warning_sms = models.BooleanField(default=True, verbose_name="Limit Warning SMS")
    notify_limit_warning_email = models.BooleanField(default=True, verbose_name="Limit Warning Email")

    notify_limit_exceeded = models.BooleanField(default=True, verbose_name="Limit Exceeded")
    notify_limit_exceeded_sms = models.BooleanField(default=True, verbose_name="Limit Exceeded SMS")
    notify_limit_exceeded_email = models.BooleanField(default=True, verbose_name="Limit Exceeded Email")

    notify_limit_reset = models.BooleanField(default=False, verbose_name="Annual Limit Reset")
    notify_limit_reset_sms = models.BooleanField(default=False, verbose_name="Limit Reset SMS")
    notify_limit_reset_email = models.BooleanField(default=True, verbose_name="Limit Reset Email")

    # =======================
    # PROVIDER ACTIVITIES NOTIFICATIONS
    # =======================

    # Provider Registration & Status
    notify_provider_registration = models.BooleanField(default=False, verbose_name="Provider Registration")
    notify_provider_registration_sms = models.BooleanField(default=False, verbose_name="Provider Registration SMS")
    notify_provider_registration_email = models.BooleanField(default=True, verbose_name="Provider Registration Email")

    notify_provider_status_change = models.BooleanField(default=False, verbose_name="Provider Status Change")
    notify_provider_status_change_sms = models.BooleanField(default=False, verbose_name="Provider Status Change SMS")
    notify_provider_status_change_email = models.BooleanField(default=True, verbose_name="Provider Status Change Email")

    # Provider Compliance
    notify_provider_document_expiry = models.BooleanField(default=False, verbose_name="Provider Document Expiry")
    notify_provider_document_expiry_sms = models.BooleanField(default=False,
                                                              verbose_name="Provider Document Expiry SMS")
    notify_provider_document_expiry_email = models.BooleanField(default=True,
                                                                verbose_name="Provider Document Expiry Email")

    notify_provider_compliance_issue = models.BooleanField(default=False, verbose_name="Provider Compliance Issues")
    notify_provider_compliance_issue_sms = models.BooleanField(default=False, verbose_name="Provider Compliance SMS")
    notify_provider_compliance_issue_email = models.BooleanField(default=True, verbose_name="Provider Compliance Email")

    notify_provider_payment = models.BooleanField(default=False, verbose_name="Provider Payment Processed")
    notify_provider_payment_sms = models.BooleanField(default=False, verbose_name="Provider Payment SMS")
    notify_provider_payment_email = models.BooleanField(default=True, verbose_name="Provider Payment Email")

    # =======================
    # AGENT COMMISSION NOTIFICATIONS
    # =======================

    notify_commission_earned = models.BooleanField(default=True, verbose_name="Commission Earned")
    notify_commission_earned_sms = models.BooleanField(default=True, verbose_name="Commission Earned SMS")
    notify_commission_earned_email = models.BooleanField(default=True, verbose_name="Commission Earned Email")

    notify_commission_bonus = models.BooleanField(default=True, verbose_name="Commission Bonus")
    notify_commission_bonus_sms = models.BooleanField(default=True, verbose_name="Commission Bonus SMS")
    notify_commission_bonus_email = models.BooleanField(default=True, verbose_name="Commission Bonus Email")

    notify_commission_threshold = models.BooleanField(default=True, verbose_name="Commission Threshold Reached")
    notify_commission_threshold_sms = models.BooleanField(default=True, verbose_name="Commission Threshold SMS")
    notify_commission_threshold_email = models.BooleanField(default=True, verbose_name="Commission Threshold Email")

    notify_commission_payment = models.BooleanField(default=True, verbose_name="Commission Payment")
    notify_commission_payment_sms = models.BooleanField(default=True, verbose_name="Commission Payment SMS")
    notify_commission_payment_email = models.BooleanField(default=True, verbose_name="Commission Payment Email")

    # =======================
    # KYC & COMPLIANCE NOTIFICATIONS
    # =======================

    notify_kyc_required = models.BooleanField(default=True, verbose_name="KYC Required")
    notify_kyc_required_sms = models.BooleanField(default=True, verbose_name="KYC Required SMS")
    notify_kyc_required_email = models.BooleanField(default=True, verbose_name="KYC Required Email")

    notify_kyc_document_uploaded = models.BooleanField(default=False, verbose_name="KYC Document Uploaded")
    notify_kyc_document_uploaded_sms = models.BooleanField(default=False, verbose_name="KYC Document Uploaded SMS")
    notify_kyc_document_uploaded_email = models.BooleanField(default=True, verbose_name="KYC Document Uploaded Email")

    notify_kyc_verified = models.BooleanField(default=True, verbose_name="KYC Verified")
    notify_kyc_verified_sms = models.BooleanField(default=True, verbose_name="KYC Verified SMS")
    notify_kyc_verified_email = models.BooleanField(default=True, verbose_name="KYC Verified Email")

    notify_kyc_rejected = models.BooleanField(default=True, verbose_name="KYC Rejected")
    notify_kyc_rejected_sms = models.BooleanField(default=True, verbose_name="KYC Rejected SMS")
    notify_kyc_rejected_email = models.BooleanField(default=True, verbose_name="KYC Rejected Email")

    notify_document_expiry = models.BooleanField(default=True, verbose_name="Document Expiry Warning")
    notify_document_expiry_sms = models.BooleanField(default=False, verbose_name="Document Expiry SMS")
    notify_document_expiry_email = models.BooleanField(default=True, verbose_name="Document Expiry Email")

    # =======================
    # SYSTEM NOTIFICATIONS
    # =======================

    # Security Alerts
    notify_login_success = models.BooleanField(default=False, verbose_name="Successful Login")
    notify_login_success_sms = models.BooleanField(default=False, verbose_name="Login Success SMS")
    notify_login_success_email = models.BooleanField(default=False, verbose_name="Login Success Email")

    notify_failed_login = models.BooleanField(default=True, verbose_name="Failed Login Attempts")
    notify_failed_login_sms = models.BooleanField(default=True, verbose_name="Failed Login SMS")
    notify_failed_login_email = models.BooleanField(default=True, verbose_name="Failed Login Email")

    notify_password_changed = models.BooleanField(default=True, verbose_name="Password Changed")
    notify_password_changed_sms = models.BooleanField(default=True, verbose_name="Password Changed SMS")
    notify_password_changed_email = models.BooleanField(default=True, verbose_name="Password Changed Email")

    notify_account_locked = models.BooleanField(default=True, verbose_name="Account Locked")
    notify_account_locked_sms = models.BooleanField(default=True, verbose_name="Account Locked SMS")
    notify_account_locked_email = models.BooleanField(default=True, verbose_name="Account Locked Email")

    # System Updates
    notify_system_maintenance = models.BooleanField(default=True, verbose_name="System Maintenance")
    notify_system_maintenance_sms = models.BooleanField(default=False, verbose_name="System Maintenance SMS")
    notify_system_maintenance_email = models.BooleanField(default=True, verbose_name="System Maintenance Email")

    notify_feature_updates = models.BooleanField(default=False, verbose_name="Feature Updates")
    notify_feature_updates_sms = models.BooleanField(default=False, verbose_name="Feature Updates SMS")
    notify_feature_updates_email = models.BooleanField(default=True, verbose_name="Feature Updates Email")

    notify_policy_changes = models.BooleanField(default=True, verbose_name="Policy Changes")
    notify_policy_changes_sms = models.BooleanField(default=False, verbose_name="Policy Changes SMS")
    notify_policy_changes_email = models.BooleanField(default=True, verbose_name="Policy Changes Email")

    # =======================
    # MARKETING & PROMOTIONAL NOTIFICATIONS
    # =======================

    notify_promotions = models.BooleanField(default=False, verbose_name="Promotions & Offers")
    notify_promotions_sms = models.BooleanField(default=False, verbose_name="Promotions SMS")
    notify_promotions_email = models.BooleanField(default=False, verbose_name="Promotions Email")

    notify_newsletters = models.BooleanField(default=False, verbose_name="Newsletters")
    notify_newsletters_sms = models.BooleanField(default=False, verbose_name="Newsletter SMS")
    notify_newsletters_email = models.BooleanField(default=True, verbose_name="Newsletter Email")

    notify_surveys = models.BooleanField(default=False, verbose_name="Surveys & Feedback")
    notify_surveys_sms = models.BooleanField(default=False, verbose_name="Survey SMS")
    notify_surveys_email = models.BooleanField(default=True, verbose_name="Survey Email")

    notify_health_tips = models.BooleanField(default=False, verbose_name="Health Tips")
    notify_health_tips_sms = models.BooleanField(default=False, verbose_name="Health Tips SMS")
    notify_health_tips_email = models.BooleanField(default=True, verbose_name="Health Tips Email")

    # =======================
    # EMERGENCY NOTIFICATIONS (Always Enabled)
    # =======================

    notify_emergency_alerts = models.BooleanField(default=True, verbose_name="Emergency Alerts")
    notify_emergency_alerts_sms = models.BooleanField(default=True, verbose_name="Emergency Alerts SMS")
    notify_emergency_alerts_email = models.BooleanField(default=True, verbose_name="Emergency Alerts Email")

    notify_fraud_alerts = models.BooleanField(default=True, verbose_name="Fraud Alerts")
    notify_fraud_alerts_sms = models.BooleanField(default=True, verbose_name="Fraud Alerts SMS")
    notify_fraud_alerts_email = models.BooleanField(default=True, verbose_name="Fraud Alerts Email")

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

    def can_receive_notification(self, activity_type: str, method: str = 'both') -> bool:
        """
        Check if user can receive notification for specific activity

        Args:
            activity_type: The notification type (e.g., 'claim_approved', 'topup_successful')
            method: 'sms', 'email', or 'both'

        Returns:
            bool: Whether the user should receive this notification
        """

        # Check global notification settings first
        if not self.receive_sms_notifications and method in ['sms', 'both']:
            return False
        if not self.receive_email_notifications and method in ['email', 'both']:
            return False

        # Check if it's quiet hours
        if method in ['sms', 'both'] and self.is_in_sms_quiet_hours():
            return False
        if method in ['email', 'both'] and self.is_in_email_quiet_hours():
            return False

        # Check specific activity notification setting
        activity_field = f'notify_{activity_type}'
        if hasattr(self, activity_field):
            if not getattr(self, activity_field):
                return False

        # Check method-specific setting
        if method == 'sms':
            sms_field = f'notify_{activity_type}_sms'
            if hasattr(self, sms_field):
                return getattr(self, sms_field)
        elif method == 'email':
            email_field = f'notify_{activity_type}_email'
            if hasattr(self, email_field):
                return getattr(self, email_field)
        elif method == 'both':
            # For both, return True if either method is enabled
            sms_field = f'notify_{activity_type}_sms'
            email_field = f'notify_{activity_type}_email'
            sms_enabled = getattr(self, sms_field, True) if hasattr(self, sms_field) else True
            email_enabled = getattr(self, email_field, True) if hasattr(self, email_field) else True
            return sms_enabled or email_enabled

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

    def get_notification_preferences_summary(self):
        """Get a summary of user's notification preferences"""

        preferences = {
            'member_activities': {
                'registration': self.can_receive_notification('member_registration'),
                'status_changes': self.can_receive_notification('member_status_change'),
                'beneficiary_changes': self.can_receive_notification('beneficiary_addition'),
            },
            'claims': {
                'submitted': self.can_receive_notification('claim_submitted'),
                'approved': self.can_receive_notification('claim_approved'),
                'declined': self.can_receive_notification('claim_declined'),
                'paid': self.can_receive_notification('claim_paid'),
            },
            'account_financial': {
                'topup_successful': self.can_receive_notification('topup_successful'),
                'low_balance': self.can_receive_notification('low_balance'),
                'limit_warning': self.can_receive_notification('limit_warning'),
            },
            'security': {
                'failed_login': self.can_receive_notification('failed_login'),
                'password_changed': self.can_receive_notification('password_changed'),
                'account_locked': self.can_receive_notification('account_locked'),
            },
            'marketing': {
                'promotions': self.can_receive_notification('promotions'),
                'newsletters': self.can_receive_notification('newsletters'),
                'health_tips': self.can_receive_notification('health_tips'),
            },
            'emergency': {
                'emergency_alerts': self.can_receive_notification('emergency_alerts'),
                'fraud_alerts': self.can_receive_notification('fraud_alerts'),
            }
        }

        return preferences

    def get_active_notification_channels(self, activity_type: str):
        """Get active notification channels for a specific activity"""

        channels = []

        if self.can_receive_notification(activity_type, 'sms'):
            channels.append('sms')

        if self.can_receive_notification(activity_type, 'email'):
            channels.append('email')

        return channels

    def bulk_update_notification_preferences(self, category: str, enabled: bool, method: str = 'both'):
        """
        Bulk update notification preferences for a category

        Args:
            category: 'claims', 'account', 'security', 'marketing', etc.
            enabled: True to enable, False to disable
            method: 'sms', 'email', or 'both'
        """

        category_mappings = {
            'claims': [
                'claim_submitted', 'claim_under_review', 'claim_approved',
                'claim_declined', 'claim_modified', 'claim_paid', 'claim_payment_failed'
            ],
            'account': [
                'topup_initiated', 'topup_successful', 'topup_failed',
                'low_balance', 'negative_balance', 'account_credited',
                'account_debited', 'limit_warning', 'limit_exceeded'
            ],
            'member': [
                'member_registration', 'member_status_change', 'member_profile_update',
                'beneficiary_addition', 'beneficiary_removal'
            ],
            'authorization': [
                'service_request_submitted', 'authorization_approved',
                'authorization_declined', 'authorization_expired', 'authorization_utilized'
            ],
            'security': [
                'login_success', 'failed_login', 'password_changed', 'account_locked'
            ],
            'kyc': [
                'kyc_required', 'kyc_document_uploaded', 'kyc_verified',
                'kyc_rejected', 'document_expiry'
            ],
            'commission': [
                'commission_earned', 'commission_bonus', 'commission_threshold', 'commission_payment'
            ],
            'provider': [
                'provider_registration', 'provider_status_change',
                'provider_document_expiry', 'provider_compliance_issue', 'provider_payment'
            ],
            'system': [
                'system_maintenance', 'feature_updates', 'policy_changes'
            ],
            'marketing': [
                'promotions', 'newsletters', 'surveys', 'health_tips'
            ]
        }

        activities = category_mappings.get(category, [])

        for activity in activities:
            # Update main notification setting
            main_field = f'notify_{activity}'
            if hasattr(self, main_field):
                setattr(self, main_field, enabled)

            # Update method-specific settings
            if method in ['sms', 'both']:
                sms_field = f'notify_{activity}_sms'
                if hasattr(self, sms_field):
                    setattr(self, sms_field, enabled)

            if method in ['email', 'both']:
                email_field = f'notify_{activity}_email'
                if hasattr(self, email_field):
                    setattr(self, email_field, enabled)

        self.save()

    def set_emergency_notifications_only(self):
        """Disable all notifications except emergency and fraud alerts"""

        # Get all notification fields
        notification_fields = [field.name for field in self._meta.fields
                               if field.name.startswith('notify_') and
                               not field.name.startswith('notify_emergency_') and
                               not field.name.startswith('notify_fraud_')]

        # Disable all non-emergency notifications
        for field_name in notification_fields:
            setattr(self, field_name, False)

        # Ensure emergency notifications are enabled
        self.notify_emergency_alerts = True
        self.notify_emergency_alerts_sms = True
        self.notify_emergency_alerts_email = True
        self.notify_fraud_alerts = True
        self.notify_fraud_alerts_sms = True
        self.notify_fraud_alerts_email = True

        self.save()

    def enable_essential_notifications_only(self):
        """Enable only essential notifications (claims, account, security)"""

        # Disable all notifications first
        notification_fields = [field.name for field in self._meta.fields
                               if field.name.startswith('notify_')]

        for field_name in notification_fields:
            setattr(self, field_name, False)

        # Enable essential notifications
        essential_notifications = [
            # Claims
            'notify_claim_approved', 'notify_claim_approved_sms', 'notify_claim_approved_email',
            'notify_claim_declined', 'notify_claim_declined_sms', 'notify_claim_declined_email',
            'notify_claim_paid', 'notify_claim_paid_sms', 'notify_claim_paid_email',

            # Account
            'notify_topup_successful', 'notify_topup_successful_sms', 'notify_topup_successful_email',
            'notify_topup_failed', 'notify_topup_failed_sms', 'notify_topup_failed_email',
            'notify_low_balance', 'notify_low_balance_sms', 'notify_low_balance_email',
            'notify_limit_exceeded', 'notify_limit_exceeded_sms', 'notify_limit_exceeded_email',

            # Security
            'notify_failed_login', 'notify_failed_login_sms', 'notify_failed_login_email',
            'notify_account_locked', 'notify_account_locked_sms', 'notify_account_locked_email',

            # Emergency
            'notify_emergency_alerts', 'notify_emergency_alerts_sms', 'notify_emergency_alerts_email',
            'notify_fraud_alerts', 'notify_fraud_alerts_sms', 'notify_fraud_alerts_email',

            # Authorization
            'notify_authorization_approved', 'notify_authorization_approved_sms', 'notify_authorization_approved_email',
            'notify_authorization_declined', 'notify_authorization_declined_sms', 'notify_authorization_declined_email',
        ]

        for field_name in essential_notifications:
            if hasattr(self, field_name):
                setattr(self, field_name, True)

        self.save()

    def get_notification_statistics(self, days: int = 30):
        """Get notification statistics for the user over specified period"""

        from datetime import timedelta
        from django.utils import timezone

        start_date = timezone.now() - timedelta(days=days)

        try:
            # Import here to avoid circular imports
            from notifications.models import NotificationLog
            
            stats = NotificationLog.objects.filter(
                notification__user=self,
                created_at__gte=start_date
            ).aggregate(
                total_sent=models.Count('id'),
                sms_sent=models.Count('id', filter=models.Q(channel='sms')),
                email_sent=models.Count('id', filter=models.Q(channel='email')),
                delivered=models.Count('id', filter=models.Q(status='delivered')),
                failed=models.Count('id', filter=models.Q(status='failed'))
            )

            stats['delivery_rate'] = (stats['delivered'] / stats['total_sent'] * 100) if stats['total_sent'] > 0 else 0

            return stats

        except Exception as e:
            logger.error(f"Error getting notification statistics for user {self.username}: {str(e)}")
            return {
                'total_sent': 0,
                'sms_sent': 0,
                'email_sent': 0,
                'delivered': 0,
                'failed': 0,
                'delivery_rate': 0
            }

    @classmethod
    def get_notification_field_choices(cls):
        """Get all notification field choices for admin interface"""

        fields = {}

        for field in cls._meta.fields:
            if field.name.startswith('notify_') and not field.name.endswith('_sms') and not field.name.endswith(
                    '_email'):
                # Main notification field
                category = field.name.replace('notify_', '').replace('_', ' ').title()
                fields[field.name] = {
                    'label': field.verbose_name,
                    'category': category,
                    'sms_field': f'{field.name}_sms',
                    'email_field': f'{field.name}_email',
                    'default': field.default
                }

        return fields

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def __str__(self):
        return self.username

    class Meta:
        ordering = ["first_name", "last_name"]
        verbose_name = "User"
        verbose_name_plural = "Users"


# Enhanced notification helper functions
def get_user_notification_preferences(user: User, activity_type: str):
    """
    Get detailed notification preferences for a user and activity

    Returns:
        dict: Detailed preferences including channels and settings
    """

    preferences = {
        'can_receive': user.can_receive_notification(activity_type),
        'channels': user.get_active_notification_channels(activity_type),
        'in_quiet_hours': {
            'sms': user.is_in_sms_quiet_hours(),
            'email': user.is_in_email_quiet_hours()
        },
        'global_settings': {
            'sms_enabled': user.receive_sms_notifications,
            'email_enabled': user.receive_email_notifications,
            'preferred_method': user.preferred_notification_method
        }
    }

    return preferences


def bulk_update_user_notifications(users, settings):
    """
    Bulk update notification settings for multiple users

    Args:
        users: QuerySet of User objects
        settings: Dict of notification settings to update
    """

    for user in users:
        for field_name, value in settings.items():
            if hasattr(user, field_name):
                setattr(user, field_name, value)
        user.save()


# Usage examples in signals and services:

# In signals.py - Enhanced notification function
def send_enhanced_notification(user, activity_type, subject, message, **kwargs):
    """
    Enhanced notification function that respects user preferences

    Args:
        user: User object
        activity_type: Type of activity (e.g., 'claim_approved')
        subject: Notification subject
        message: Notification message
        **kwargs: Additional parameters
    """

    from services.notification_service import NotificationService

    # Check if user can receive this notification
    if not user.can_receive_notification(activity_type):
        return {'sent': False, 'reason': 'User disabled this notification type'}

    # Get active channels
    channels = user.get_active_notification_channels(activity_type)

    if not channels:
        return {'sent': False, 'reason': 'No active notification channels'}

    # Send notification via active channels
    notification_service = NotificationService()

    results = {}

    if 'sms' in channels:
        sms_result = notification_service.send_sms_notification(
            phone=user.get_notification_phone(),
            message=message,
            message_type=kwargs.get('message_type', 'notification'),
            priority=kwargs.get('priority', 'normal')
        )
        results['sms'] = sms_result

    if 'email' in channels:
        email_result = notification_service.send_email_notification(
            email=user.email,
            subject=subject,
            message=message,
            template=kwargs.get('template'),
            context=kwargs.get('context')
        )
        results['email'] = email_result

    return results


# Example usage in claim signals:
def send_claim_approval_notification(claim):
    """Send claim approval notification respecting user preferences"""

    user = claim.beneficiary.member.signatories.first()  # Get primary user

    if user:
        result = send_enhanced_notification(
            user=user,
            activity_type='claim_approved',
            subject=f'Claim Approved - {claim.transaction_number}',
            message=f'Your claim {claim.transaction_number} for ${claim.accepted_amount} has been approved.',
            message_type='notification',
            priority='normal'
        )

        logger.info(f"Claim approval notification sent to {user.username}: {result}")


# Example usage in top-up signals:
def send_topup_confirmation(topup):
    """Send top-up confirmation respecting user preferences"""

    user = topup.member.signatories.first()

    if user:
        result = send_enhanced_notification(
            user=user,
            activity_type='topup_successful',
            subject=f'Top-up Successful - {topup.top_up_number}',
            message=f'Top-up of ${topup.net_amount} successful. New balance: ${topup.account.available_balance}',
            message_type='notification',
            priority='normal'
        )

        logger.info(f"Top-up confirmation sent to {user.username}: {result}")