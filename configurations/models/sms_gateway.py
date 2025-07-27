from django.db import models
from django.utils import timezone

from configurations.models.base_model import BaseModel


class SMSGateway(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Gateway Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    # Gateway Configuration
    base_url = models.URLField(verbose_name="Base URL")
    api_endpoint = models.CharField(max_length=255, verbose_name="API Endpoint")

    # Authentication Method
    AUTH_TYPES = [
        ('header', 'Header Credentials'),
        ('basic', 'Basic Authentication'),
        ('bearer', 'Bearer Token'),
        ('api_key', 'API Key'),
    ]
    auth_type = models.CharField(max_length=10, choices=AUTH_TYPES, default='header',
                                 verbose_name="Authentication Type")

    # Credentials
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="Username")
    password = models.CharField(max_length=255, blank=True, null=True, verbose_name="Password")
    api_key = models.CharField(max_length=500, blank=True, null=True, verbose_name="API Key")
    sender_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Sender ID")

    # Configuration
    max_message_length = models.PositiveIntegerField(default=160, verbose_name="Max Message Length")
    supports_unicode = models.BooleanField(default=False, verbose_name="Supports Unicode")
    supports_delivery_reports = models.BooleanField(default=False, verbose_name="Supports Delivery Reports")

    # Rate Limiting
    rate_limit_per_minute = models.PositiveIntegerField(default=100, verbose_name="Rate Limit per Minute")
    cost_per_sms = models.DecimalField(max_digits=10, decimal_places=4, default=0,
                                       verbose_name="Cost per SMS")

    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    is_primary = models.BooleanField(default=False, verbose_name="Is Primary Gateway")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one primary gateway
        if self.is_primary:
            SMSGateway.objects.exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "SMS Gateway"
        verbose_name_plural = "SMS Gateways"
        ordering = ['-is_primary', 'name']


class SMSGatewayMapping(BaseModel):
    gateway = models.ForeignKey(SMSGateway, on_delete=models.CASCADE, related_name="field_mappings")

    # Field mappings for SMS requests
    FIELD_TYPES = [
        ('recipient', 'Recipient Number'),
        ('message', 'Message Content'),
        ('sender', 'Sender ID'),
        ('message_id', 'Message ID'),
        ('callback_url', 'Callback URL'),
        ('priority', 'Priority'),
        ('validity_period', 'Validity Period'),
        ('flash', 'Flash Message'),
    ]
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, verbose_name="Field Type")
    gateway_field_name = models.CharField(max_length=255, verbose_name="Gateway Field Name")
    is_required = models.BooleanField(default=False, verbose_name="Is Required")
    default_value = models.CharField(max_length=500, blank=True, null=True, verbose_name="Default Value")

    # Transformation rules
    format_rule = models.CharField(max_length=500, blank=True, null=True, verbose_name="Format Rule (e.g., +263{number})")


    def __str__(self):
        return f"{self.gateway.name} - {self.field_type}"

    class Meta:
        unique_together = [("gateway", "field_type")]
        verbose_name = "SMS Gateway Mapping"
        verbose_name_plural = "SMS Gateway Mappings"


class SMSMessage(BaseModel):
    gateway = models.ForeignKey(SMSGateway, on_delete=models.CASCADE, related_name="messages")

    # Message Details
    message_id = models.CharField(max_length=255, unique=True, verbose_name="Message ID")
    recipient_number = models.CharField(max_length=20, verbose_name="Recipient Number")
    sender_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Sender ID")
    message_content = models.TextField(verbose_name="Message Content")

    # Message Type
    MESSAGE_TYPES = [
        ('notification', 'Notification'),
        ('alert', 'Alert'),
        ('otp', 'OTP'),
        ('marketing', 'Marketing'),
        ('reminder', 'Reminder'),
    ]
    message_type = models.CharField(max_length=15, choices=MESSAGE_TYPES, default='notification',
                                    verbose_name="Message Type")

    # Priority
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal',
                                verbose_name="Priority")

    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending',
                              verbose_name="Status")

    # Gateway Response
    gateway_message_id = models.CharField(max_length=255, blank=True, null=True,
                                          verbose_name="Gateway Message ID")
    gateway_response = models.JSONField(default=dict, verbose_name="Gateway Response")

    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Sent At")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="Delivered At")

    # Cost
    cost = models.DecimalField(max_digits=10, decimal_places=4, default=0, verbose_name="Cost")

    # Retry Logic
    retry_count = models.PositiveIntegerField(default=0, verbose_name="Retry Count")
    max_retries = models.PositiveIntegerField(default=3, verbose_name="Max Retries")

    # Related Models
    member = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="sms_messages")
    service_provider = models.ForeignKey('ServiceProvider', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name="sms_messages")
    agent = models.ForeignKey('Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name="sms_messages")


    def save(self, *args, **kwargs):
        if not self.message_id:
            import uuid
            self.message_id = f"SMS{timezone.now().strftime('%y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.message_id} - {self.recipient_number}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "SMS Message"
        verbose_name_plural = "SMS Messages"
