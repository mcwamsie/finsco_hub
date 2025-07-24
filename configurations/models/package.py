from django.db import models

from configurations.models.base_model import BaseModel
from configurations.models.service_provider import ServiceProviderType


# class Package(BaseModel):
#     name = models.CharField(max_length=255, unique=True, verbose_name="Package Name")
#     description = models.TextField(blank=True, null=True, verbose_name="Description")
#
#     # Global Limits
#     global_annual_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Global Annual Limit")
#     global_family_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Global Family Annual Limit")
#
#     # Contribution amounts
#     monthly_contribution = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Monthly Contribution")
#     child_monthly_contribution = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Child Monthly Contribution")
#
#     # Package status
#     is_active = models.BooleanField(default=True, verbose_name="Is Active")
#
#     def __str__(self):
#         return self.name.upper()
#
#     class Meta:
#         ordering = ["name"]
#         verbose_name = "Package"
#         verbose_name_plural = "Packages"
#
# class PackageLimit(BaseModel):
#     package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="limits")
#     service_provider_type = models.ForeignKey(ServiceProviderType, on_delete=models.CASCADE, related_name="package_limits")
#
#     # Limit types
#     annual_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Annual Limit")
#     per_visit_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Per Visit Limit")
#     max_visits_per_year = models.PositiveIntegerField(default=0, verbose_name="Max Visits Per Year")
#
#     # Co-payment
#     co_payment_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Co-payment %")
#     co_payment_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Co-payment Amount")
#
#     # Waiting periods
#     waiting_period_days = models.PositiveIntegerField(default=0, verbose_name="Waiting Period (Days)")
#
#     def __str__(self):
#         return f"{self.package.name} - {self.service_provider_type.name}"
#
#     class Meta:
#         unique_together = [("package", "service_provider_type")]
#         ordering = ["package", "service_provider_type"]
#         verbose_name = "Package Limit"
#         verbose_name_plural = "Package Limits"

class Package(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Package Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    # Global Limits
    global_annual_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Global Annual Limit")
    global_family_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Global Family Annual Limit")

    # Contribution amounts
    monthly_contribution = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Monthly Contribution")
    child_monthly_contribution = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Child Monthly Contribution")

    # Package status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    def __str__(self):
        return self.name.upper()

    class Meta:
        ordering = ["name"]
        verbose_name = "Package"
        verbose_name_plural = "Packages"


class PackageLimit(BaseModel):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="limits")
    service_provider_type = models.ForeignKey('configurations.ServiceProviderType', on_delete=models.CASCADE,  related_name="package_limits")

    # Limit types
    annual_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0,  verbose_name="Annual Limit")
    per_visit_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Per Visit Limit")
    max_visits_per_year = models.PositiveIntegerField(default=0, verbose_name="Max Visits Per Year")

    # Co-payment
    co_payment_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Co-payment %")
    co_payment_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Co-payment Amount")

    # Waiting periods
    waiting_period_days = models.PositiveIntegerField(default=0, verbose_name="Waiting Period (Days)")

    def __str__(self):
        return f"{self.package.name} - {self.service_provider_type.name}"

    class Meta:
        unique_together = [("package", "service_provider_type")]
        ordering = ["package", "service_provider_type"]
        verbose_name = "Package Limit"
        verbose_name_plural = "Package Limits"
