from django.db import models

from configurations.models import Currency
from configurations.models.base_model import BaseModel
from configurations.models.payment_gateway import PaymentGateway


class PaymentMethod(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Payment Method Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    # Method Configuration
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name="payment_methods", verbose_name="Currency")
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.CASCADE, related_name="payment_methods", verbose_name="Payment Gateway")
    gateway_method_code = models.CharField(max_length=100, verbose_name="Gateway Method Code")

    # Limits
    min_amount = models.DecimalField(max_digits=11, decimal_places=2, verbose_name="Minimum Amount")
    max_amount = models.DecimalField(max_digits=11, decimal_places=2, verbose_name="Maximum Amount")

    # Method Type
    TYPE_CHOICES = [
        ("C", "Cash"),
        ("E", "Electronic"),
        ("O", "Offline"),
        ("MM", "Mobile Money"),
        ("CC", "Credit Card"),
        ("DC", "Debit Card"),
        ("BT", "Bank Transfer"),
    ]
    type = models.CharField(max_length=2, choices=TYPE_CHOICES, default="O", verbose_name="Method Type")

    # Processing Configuration
    processing_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Processing Fee %")
    processing_fee_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Processing Fee (Fixed)")

    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    sort_order = models.PositiveIntegerField(default=100, verbose_name="Sort Order")

    def __str__(self):
        return f"{self.name} ({self.currency.code})"

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"
        unique_together = [("gateway", "gateway_method_code")]


