from django.contrib.auth import get_user_model
from django.db import models

from configurations.models.base_model import BaseModel

User = get_user_model()

class AdjudicationOverride(BaseModel):
    claim = models.ForeignKey('services.Claim', on_delete=models.CASCADE, related_name="overrides")
    adjudicator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="adjudication_overrides")

    # Original decision details
    original_result = models.CharField(max_length=20, blank=True, null=True, verbose_name="Original Result")
    original_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Original Amount")

    # New decision details
    NEW_DECISION_CHOICES = [
        ('APPROVED', 'Manually Approved'),
        ('DECLINED', 'Manually Declined'),
        ('MODIFIED', 'Amount Modified'),
        ('RETURNED_TO_AUTO', 'Returned to Auto-Adjudication'),
    ]
    new_decision = models.CharField(max_length=20, choices=NEW_DECISION_CHOICES, verbose_name="New Decision")
    new_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="New Amount")

    # Override details
    override_reason = models.TextField(verbose_name="Override Reason")
    review_notes = models.TextField(blank=True, null=True, verbose_name="Review Notes")
    override_timestamp = models.DateTimeField(verbose_name="Override Timestamp")

    # Approval workflow
    requires_approval = models.BooleanField(default=False, verbose_name="Requires Approval")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_overrides", verbose_name="Approved By")
    approval_timestamp = models.DateTimeField(null=True, blank=True, verbose_name="Approval Timestamp")

    # Impact tracking
    financial_impact = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Financial Impact")

    def save(self, *args, **kwargs):
        # Calculate financial impact
        if self.original_amount and self.new_amount:
            self.financial_impact = self.new_amount - self.original_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Override for {self.claim.transaction_number} by {self.adjudicator.username}"

    class Meta:
        verbose_name = "Adjudication Override"
        verbose_name_plural = "Adjudication Overrides"
        ordering = ['-override_timestamp']
