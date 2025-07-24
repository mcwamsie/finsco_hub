from django.db import models

from configurations.models.base_model import BaseModel
from configurations.models.tier import Tier


class ServiceProviderType(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Type Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    requires_license = models.BooleanField(default=False, verbose_name="Requires License")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    def __str__(self):
        return self.name.upper()

    class Meta:
        verbose_name = "Service Provider Type"
        verbose_name_plural = "Service Provider Types"
        ordering = ["name"]


class ServiceProviderDocumentType(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Document Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    is_mandatory = models.BooleanField(default=False, verbose_name="Is Mandatory")
    has_expiry_date = models.BooleanField(default=False, verbose_name="Has Expiry Date")
    reminder_days_before_expiry = models.PositiveIntegerField(default=30,
                                                              verbose_name="Reminder Days Before Expiry")


    def __str__(self):
        return self.name.upper()

    class Meta:
        verbose_name = "Service Provider Document Type"
        verbose_name_plural = "Service Provider Document Types"
        ordering = ["name"]


class ServiceProviderTypeRequirement(BaseModel):
    provider_type = models.ForeignKey(ServiceProviderType, on_delete=models.CASCADE,
                                      related_name="requirements")
    document_type = models.ForeignKey(ServiceProviderDocumentType, on_delete=models.CASCADE,
                                      related_name="type_requirements")
    is_required = models.BooleanField(default=True, verbose_name="Is Required")
    withhold_payment_if_missing = models.BooleanField(default=False,
                                                      verbose_name="Withhold Payment If Missing")
    withhold_payment_if_expired = models.BooleanField(default=False,
                                                      verbose_name="Withhold Payment If Expired")
    withhold_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                              verbose_name="Withhold Percentage")
    withhold_fixed_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                                verbose_name="Withhold Fixed Amount")


    def __str__(self):
        return f"{self.provider_type.name} - {self.document_type.name}"

    class Meta:
        unique_together = [("provider_type", "document_type")]
        verbose_name = "Service Provider Type Requirement"
        verbose_name_plural = "Service Provider Type Requirements"


# configurations/models/service_provider.py
class ServiceProvider(BaseModel):
    account_no = models.CharField(max_length=255, unique=True, editable=False, db_index=True, verbose_name="Account Number")
    logo = models.ImageField(max_length=255, upload_to="provider/logo", null=True, blank=True, verbose_name="Logo")
    name = models.CharField(max_length=255, unique=True, verbose_name="Name", db_index=True)
    alias = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name="Alias")
    identification_no = models.CharField(max_length=255, verbose_name="AFHOZ No.")

    # Contact information
    address_line_1 = models.CharField(max_length=255, verbose_name="Address Line 1")
    address_line_2 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Address Line 2")
    address_line_3 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Address Line 3")

    # Phone
    mobile = models.CharField(max_length=20, verbose_name="Mobile Number")
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telephone")
    email = models.EmailField(max_length=255, verbose_name="Email Address")

    # Classifications
    tier = models.ForeignKey(Tier, on_delete=models.CASCADE, related_name="service_providers", verbose_name="Provider Tier")
    type = models.ForeignKey(ServiceProviderType, on_delete=models.CASCADE, related_name="service_providers", verbose_name="Provider Type")

    date_joined = models.DateField(auto_now_add=True, editable=False, verbose_name="Date Joined")

    # Business details
    status = models.CharField(max_length=1, choices=[("A", "Active"), ("I", "Inactive"), ("S", "Suspended")], default="A")
    bp_number = models.CharField(max_length=255, blank=True, null=True, verbose_name="TIN Number")
    council_number = models.CharField(max_length=255, blank=True, null=True, verbose_name="Council/Professional No")
    hpa_number = models.CharField(max_length=255, blank=True, null=True, verbose_name="HPA No")
    is_from_network = models.BooleanField(default=False, verbose_name="Is a network service provider")
    is_third_party = models.BooleanField(default=False, verbose_name="Is a third party service provider")
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE,  related_name="sub_units", verbose_name="Parent Provider")

    def __str__(self):
        if self.parent:
            return str(self.parent) + "/" + self.name.upper()
        return self.name.upper()

    def save(self, *args, **kwargs):
        if not self.account_no:
            import datetime
            from sequences import Sequence
            month = datetime.datetime.now().strftime("%Y%m")
            sequence_number = Sequence("service_provider_" + month).get_next_value()
            import random
            import string
            random_number = ''.join(random.choice(string.digits) for _ in range(2))
            self.account_no = f"{month}{sequence_number:04d}{random_number}"

        if self.parent:
            self.identification_no = self.parent.identification_no
            self.type = self.parent.type
            self.logo = self.parent.logo

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["tier", "type", "name"]
        verbose_name_plural = "Service Providers"
        verbose_name = "Service Provider"
        unique_together = [("name", "parent")]


class ServiceProviderDocument(BaseModel):
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name="documents")
    document_type = models.ForeignKey(ServiceProviderDocumentType, on_delete=models.CASCADE, related_name="provider_documents")
    document_file = models.FileField(upload_to="service_provider/documents/", verbose_name="Document File")
    document_number = models.CharField(max_length=255, blank=True, null=True, verbose_name="Document Number")
    issue_date = models.DateField(null=True, blank=True, verbose_name="Issue Date")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Expiry Date")
    issuing_authority = models.CharField(max_length=255, blank=True, null=True, verbose_name="Issuing Authority")

    STATUS_CHOICES = [
        ("V", "Valid"),
        ("E", "Expired"),
        ("P", "Pending"),
        ("R", "Rejected"),
    ]
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P", verbose_name="Document Status")

    verified_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Verified By")
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Verified At")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")


    @property
    def is_expired(self):
        if self.expiry_date:
            from django.utils import timezone
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def expires_soon(self):
        if self.expiry_date and self.document_type.reminder_days_before_expiry:
            from django.utils import timezone
            from datetime import timedelta
            warning_date = self.expiry_date - timedelta(days=self.document_type.reminder_days_before_expiry)
            return timezone.now().date() >= warning_date
        return False

    def __str__(self):
        return f"{self.service_provider.name} - {self.document_type.name}"

    class Meta:
        unique_together = [("service_provider", "document_type")]
        verbose_name = "Service Provider Document"
        verbose_name_plural = "Service Provider Documents"
        ordering = ["service_provider", "document_type"]
