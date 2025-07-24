from django.db import models

from configurations.models.base_model import BaseModel


class TopUpProcessing(BaseModel):
    top_up = models.OneToOneField('membership.TopUp', on_delete=models.CASCADE, related_name="processing_details")

    # Processing Steps
    PROCESSING_STEPS = [
        ("initiated", "Initiated"),
        ("validation", "Validation"),
        ("gateway_request", "Gateway Request"),
        ("gateway_response", "Gateway Response"),
        ("verification", "Verification"),
        ("completion", "Completion"),
        ("notification", "Notification"),
    ]
    current_step = models.CharField(max_length=20, choices=PROCESSING_STEPS, default="initiated",
                                    verbose_name="Current Step")

    # Step completion tracking
    step_completion = models.JSONField(default=dict, verbose_name="Step Completion Status")

    # Validation Details
    validation_errors = models.JSONField(default=list, verbose_name="Validation Errors")
    is_amount_valid = models.BooleanField(default=False, verbose_name="Amount Valid")
    is_method_available = models.BooleanField(default=False, verbose_name="Method Available")
    is_account_active = models.BooleanField(default=False, verbose_name="Account Active")

    # Gateway Processing
    gateway_request_sent_at = models.DateTimeField(null=True, blank=True,
                                                   verbose_name="Gateway Request Sent At")
    gateway_response_received_at = models.DateTimeField(null=True, blank=True,
                                                        verbose_name="Gateway Response Received At")
    gateway_processing_time = models.PositiveIntegerField(null=True, blank=True,
                                                          verbose_name="Gateway Processing Time (ms)")

    # Retry Logic
    retry_count = models.PositiveIntegerField(default=0, verbose_name="Retry Count")
    max_retries = models.PositiveIntegerField(default=3, verbose_name="Max Retries")
    next_retry_at = models.DateTimeField(null=True, blank=True, verbose_name="Next Retry At")

    # Callback Processing
    callback_received = models.BooleanField(default=False, verbose_name="Callback Received")
    callback_data = models.JSONField(default=dict, verbose_name="Callback Data")
    callback_verified = models.BooleanField(default=False, verbose_name="Callback Verified")

    # Completion Details
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    completion_notes = models.TextField(blank=True, null=True, verbose_name="Completion Notes")

    # Error Handling
    has_errors = models.BooleanField(default=False, verbose_name="Has Errors")
    error_details = models.JSONField(default=dict, verbose_name="Error Details")

    def __str__(self):
        return f"Processing for {self.top_up.top_up_number}"

    class Meta:
        verbose_name = "Top-up Processing"
        verbose_name_plural = "Top-up Processing"

