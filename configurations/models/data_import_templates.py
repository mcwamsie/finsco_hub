from django.db import models


class ImportTemplate(models.Model):
    """Template model to generate sample import files"""

    TEMPLATE_TYPES = [
        ('currency', 'Currency'),
        ('tier', 'Tier'),
        ('package', 'Package'),
        ('member', 'Member'),
        ('beneficiary', 'Beneficiary'),
        ('service_provider', 'Service Provider'),
        ('service', 'Service'),
        ('agent', 'Agent'),
        ('kyc_requirement', 'KYC Requirement'),
        ('adjudication_rule', 'Adjudication Rule'),
        ('service_tier_price', 'Service Tier Price'),
    ]

    name = models.CharField(max_length=100, choices=TEMPLATE_TYPES, unique=True)
    description = models.TextField(blank=True, null=True)
    sample_data = models.JSONField(default=dict, help_text="Sample data for template generation")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.get_name_display()

    class Meta:
        verbose_name = "Import Template"
        verbose_name_plural = "Import Templates"
