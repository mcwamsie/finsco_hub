from django.db import models

from configurations.models.base_model import BaseModel


class PaymentGateway(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Gateway Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    # Gateway Configuration
    base_url = models.URLField(verbose_name="Base URL")
    api_version = models.CharField(max_length=50, blank=True, null=True, verbose_name="API Version")

    # Authentication
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="Username")
    password = models.CharField(max_length=255, blank=True, null=True, verbose_name="Password")
    api_key = models.CharField(max_length=500, blank=True, null=True, verbose_name="API Key")
    secret_key = models.CharField(max_length=500, blank=True, null=True, verbose_name="Secret Key")

    # Configuration
    timeout_seconds = models.PositiveIntegerField(default=30, verbose_name="Timeout (Seconds)")
    retry_attempts = models.PositiveIntegerField(default=3, verbose_name="Retry Attempts")

    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    is_test_mode = models.BooleanField(default=False, verbose_name="Is Test Mode")

    # Supported operations
    supports_payment = models.BooleanField(default=True, verbose_name="Supports Payment")
    supports_refund = models.BooleanField(default=False, verbose_name="Supports Refund")
    supports_inquiry = models.BooleanField(default=False, verbose_name="Supports Inquiry")
    supports_cancel = models.BooleanField(default=False, verbose_name="Supports Cancel")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Payment Gateway"
        verbose_name_plural = "Payment Gateways"
        ordering = ["name"]


class PaymentGatewayMapping(BaseModel):
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE, related_name="mappings")

    # Field mappings for requests
    FIELD_TYPES = [
        ("amount", "Amount"),
        ("currency", "Currency"),
        ("reference", "Reference"),
        ("phone", "Phone Number"),
        ("email", "Email"),
        ("description", "Description"),
        ("callback_url", "Callback URL"),
        ("return_url", "Return URL"),
        ("merchant_id", "Merchant ID"),
        ("timestamp", "Timestamp"),
        ("signature", "Signature"),
    ]
    field_type = models.CharField(max_length=50, choices=FIELD_TYPES, verbose_name="Field Type")
    gateway_field_name = models.CharField(max_length=255, verbose_name="Gateway Field Name")
    is_required = models.BooleanField(default=False, verbose_name="Is Required")
    default_value = models.CharField(max_length=500, blank=True, null=True, verbose_name="Default Value")
    transformation_rule = models.TextField(blank=True, null=True, verbose_name="Transformation Rule (JSON)")

    def __str__(self):
        return f"{self.gateway.name} - {self.field_type}"

    class Meta:
        unique_together = [("gateway", "field_type")]
        verbose_name = "Payment Gateway Mapping"
        verbose_name_plural = "Payment Gateway Mappings"

class PaymentGatewayRequest(BaseModel):
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE, related_name="requests")
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.CASCADE, related_name="requests")

    # Request Details
    request_id = models.CharField(max_length=255, unique=True, verbose_name="Request ID")

    REQUEST_TYPES = [
        ("payment", "Payment"),
        ("refund", "Refund"),
        ("inquiry", "Inquiry"),
        ("cancel", "Cancel"),
    ]
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES, verbose_name="Request Type")

    # Request Data
    request_url = models.URLField(verbose_name="Request URL")
    request_method = models.CharField(max_length=10, default="POST", verbose_name="HTTP Method")
    request_headers = models.JSONField(default=dict, verbose_name="Request Headers")
    request_data = models.JSONField(default=dict, verbose_name="Request Data")

    # Response Data
    response_status_code = models.PositiveIntegerField(null=True, blank=True,
                                                       verbose_name="Response Status Code")
    response_headers = models.JSONField(default=dict, verbose_name="Response Headers")
    response_data = models.JSONField(default=dict, verbose_name="Response Data")

    # Timing
    request_timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Request Timestamp")
    response_timestamp = models.DateTimeField(null=True, blank=True, verbose_name="Response Timestamp")
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True, verbose_name="Processing Time (ms)")

    # Status
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("timeout", "Timeout"),
        ("error", "Error"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Request Status")

    # Error handling
    error_message = models.TextField(blank=True, null=True, verbose_name="Error Message")
    retry_count = models.PositiveIntegerField(default=0, verbose_name="Retry Count")

    # Links
    related_transaction = models.CharField(max_length=255, blank=True, null=True, verbose_name="Related Transaction")

    def __str__(self):
        return f"{self.request_id} - {self.gateway.name}"

    class Meta:
        ordering = ["-request_timestamp"]
        verbose_name = "Payment Gateway Request"
        verbose_name_plural = "Payment Gateway Requests"
