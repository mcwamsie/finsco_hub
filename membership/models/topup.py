from django.db import models

from configurations.models.base_model import BaseModel


class TopUp(BaseModel):
    member = models.ForeignKey('configurations.Member', on_delete=models.CASCADE, related_name="top_ups")
    account = models.ForeignKey('accounting.MemberAccount', on_delete=models.CASCADE, related_name="top_ups")
    # Payment Details
    top_up_number = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Top-up Number")
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="Top-up Amount")
    admin_fee = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Administration Fee")
    photo = models.ImageField(upload_to='topup_photos/', null=True, blank=True, verbose_name="Receipt Photo")
    # Payment Method
    payment_method = models.ForeignKey('configurations.PaymentMethod', on_delete=models.CASCADE, related_name="top_ups", verbose_name="Payment Method")

    # Payment Gateway Details
    gateway_request = models.ForeignKey('configurations.PaymentGatewayRequest', on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name="top_ups")
    gateway_reference = models.CharField(max_length=255, blank=True, null=True,
                                         verbose_name="Gateway Reference")
    gateway_response = models.JSONField(default=dict, verbose_name="Gateway Response")

    # Status
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("PR", "Processing"),
        ("S", "Successful"),
        ("F", "Failed"),
        ("C", "Cancelled"),
        ("R", "Refunded"),
    ]
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default="P",
                              verbose_name="Top-up Status")

    # Dates
    request_date = models.DateTimeField(auto_now_add=True, verbose_name="Request Date")
    completed_date = models.DateTimeField(null=True, blank=True, verbose_name="Completed Date")

    # Mobile Money Details (if applicable)
    mobile_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Mobile Number")
    mobile_network = models.CharField(max_length=50, blank=True, null=True, verbose_name="Mobile Network")

    # Bank Transfer Details (if applicable)
    bank_reference = models.CharField(max_length=255, blank=True, null=True, verbose_name="Bank Reference")

    def save(self, *args, **kwargs):
        if not self.top_up_number:
            import datetime
            from sequences import Sequence
            date_str = datetime.datetime.now().strftime("%y%m%d")
            sequence_number = Sequence(f"topup_{date_str}").get_next_value()
            self.top_up_number = f"TU{date_str}{sequence_number:06d}"

        # Calculate net amount (amount - admin fee)
        self.net_amount = self.amount - self._admin_fee
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.top_up_number} - {self.member.membership_number}"

    def start_processing(self):
        from accounting.models.topup_processing import TopUpProcessing
        """Initialize processing workflow"""
        processing, created = TopUpProcessing.objects.get_or_create(
            top_up=self,
            defaults={
                'current_step': 'initiated',
                'step_completion': {},
                'validation_errors': []
            }
        )
        return processing

    def update_processing_step(self, step, status=True, notes=None):
        from django.utils import timezone
        """Update processing step status"""
        if hasattr(self, 'processing_details'):
            processing = self.processing_details
            processing.step_completion[step] = {
                'completed': status,
                'completed_at': timezone.now().isoformat(),
                'notes': notes
            }
            processing.save()

    class Meta:
        ordering = ["-request_date"]
        verbose_name = "Top Up"
        verbose_name_plural = "Top Ups"