from django.db import models

from configurations.models import ServiceProviderType, Tier
from configurations.models.base_model import BaseModel


class Service(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Service Code", db_index=True)
    description = models.CharField(max_length=500, verbose_name="Service Description")
    service_provider_type = models.ForeignKey(ServiceProviderType, on_delete=models.CASCADE, related_name="services", verbose_name="Category")

    # Unit and pricing
    unit_of_measure = models.CharField(max_length=50, verbose_name="Unit of Measure", default="Each")
    base_price = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Base Price")

    # Service characteristics
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    requires_authorization = models.BooleanField(default=False, verbose_name="Requires Authorization")
    requires_referral = models.BooleanField(default=False, verbose_name="Requires Referral")
    is_emergency_service = models.BooleanField(default=False, verbose_name="Is Emergency Service")

    def __str__(self):
        return f"{self.code} - {self.description}"

    class Meta:
        ordering = ["service_provider_type", "code"]
        verbose_name = "Service"
        verbose_name_plural = "Services"


class ServiceModifier(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="Modifier Code", db_index=True)
    description = models.CharField(max_length=500, verbose_name="Modifier Description")

    class Meta:
        ordering = ["code"]
        verbose_name = "Service Modifier"
        verbose_name_plural = "Service Modifiers"

class ServiceTierPrice(BaseModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="tier_prices")
    tier = models.ForeignKey(Tier, on_delete=models.CASCADE, related_name="service_prices")
    highest_amount_paid = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Highest Amount Paid")
    recommended_price = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Recommended Price")
    max_payable_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Maximum Payable Amount")
    effective_from = models.DateField(verbose_name="Effective From")
    effective_to = models.DateField(null=True, blank=True, verbose_name="Effective To")

    def __str__(self):
        return f"{self.service.code} - {self.tier.name}"

    class Meta:
        unique_together = [("service", "tier", "effective_from")]
        ordering = ["service", "tier", "-effective_from"]
        verbose_name = "Service Tier Price"
        verbose_name_plural = "Service Tier Prices"
