from django.db import models

from configurations.models.base_model import BaseModel


class Claim(BaseModel):
    transaction_number = models.CharField(max_length=20, unique=True, verbose_name="Transaction Number")
    invoice_number = models.CharField(max_length=255, verbose_name="Invoice Number")
    claimed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Claimed Amount")
    accepted_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Accepted Amount")
    adjudicated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Adjudicated Amount")
    shortfall_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Shortfall Amount")
    previously_paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Previously Paid Amount")
    paid_to_provider_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Paid to Provider Amount")
    paid_to_member_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Paid to Member Amount")
    admin_fee = models.DecimalField(max_digits=20, default=0, decimal_places=3, verbose_name="Administration Fee")
    paid_date = models.DateTimeField(null=True, blank=True, verbose_name="Paid Date")

    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE, verbose_name="Submitted By")

    WHOM_TO_PAY_CHOICES = [
        ("P", "Provider"),
        ("M", "Member"),
        ("B", "Both"),
    ]
    whom_to_pay = models.CharField(max_length=1, choices=WHOM_TO_PAY_CHOICES, verbose_name="Whom To Pay")

    rate = models.DecimalField(max_digits=14, decimal_places=8, default=1, verbose_name="Exchange Rate")
    beneficiary = models.ForeignKey('membership.Beneficiary', on_delete=models.CASCADE, verbose_name="Beneficiary")
    provider = models.ForeignKey('configurations.ServiceProvider', verbose_name="Service Provider", on_delete=models.CASCADE)
    service_request = models.ForeignKey('ServiceRequest', blank=True, null=True, on_delete=models.CASCADE, related_name="claims", verbose_name="Related Service Request")
    referring_provider_number = models.CharField(max_length=255, null=True, blank=True, verbose_name="Referring Provider Number")
    referring_provider_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Referring Provider Name")

    STATUS_CHOICES = [
        ("N", "New"),
        ("U", "Under Review"),
        ("A", "Approved"),
        ("P", "Paid"),
        ("D", "Declined"),
        ("C", "Cancelled"),
    ]
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="N", verbose_name="Status")

    reversed = models.BooleanField(default=False, verbose_name="Reversed")
    wellness_visit = models.BooleanField(default=False, verbose_name="Is Wellness Visit")
    automatic_adjudication = models.BooleanField(default=False, verbose_name="Automatic Adjudication")
    manual_adjudication = models.BooleanField(default=False, verbose_name="Manual Adjudication")
    start_date = models.DateField(verbose_name="Service Start Date")
    end_date = models.DateField(verbose_name="Service End Date")

    def save(self, *args, **kwargs):
        if not self.transaction_number:
            from sequences import Sequence
            afhoz_number = self.provider.identification_no
            sequence_number = Sequence(f"claim-{afhoz_number}").get_next_value()
            self.transaction_number = f"CL.{afhoz_number}.{sequence_number:04d}"

        # Set service dates from service lines if not provided
        if hasattr(self, 'services') and self.services.exists():
            service_dates = self.services.values_list('service_date', flat=True)
            if service_dates:
                self.start_date = min(service_dates)
                self.end_date = max(service_dates)

        if not hasattr(self, 'start_date') or not self.start_date:
            from django.utils import timezone
            self.start_date = timezone.now().date()
            self.end_date = timezone.now().date()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Claim"
        verbose_name_plural = "Claims"
        ordering = ["-created_at"]
        unique_together = ["provider", "invoice_number"]


class ClaimServiceLine(BaseModel):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="services")
    service = models.ForeignKey('configurations.Service', on_delete=models.CASCADE, related_name="claim_lines")

    service_date = models.DateField(verbose_name="Service Date")
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Unit Price")
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=1, verbose_name="Quantity")
    claimed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Claimed Amount")
    accepted_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Accepted Amount")
    adjudicated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0,  verbose_name="Adjudicated Amount")
    shortfall_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Shortfall Amount")
    previously_paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Previously Paid Amount")
    paid_to_provider_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Paid to Provider Amount")
    paid_to_member_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Paid to Member Amount")

    def save(self, *args, **kwargs):
        # Calculate claimed amount
        self.claimed_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.claim.transaction_number} - {self.service.description}"

    class Meta:
        ordering = ["service__code"]
        verbose_name = "Claim Service Line"
        verbose_name_plural = "Claim Service Lines"
