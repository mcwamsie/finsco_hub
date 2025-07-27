from django.db import models

from configurations.models.base_model import BaseModel


class Bank(BaseModel):
    name = models.CharField(max_length=255)
    BANK_TYPES = [
        ("C", "Commercial Bank"),
        ("B", "Building Society"),
        ("M", "Microfinance Bank"),
        ("S", "Savings and Credit Cooperative"),
        ("I", "Investment Bank"),
        ("D", "Development Finance Institution"),
        ("O", "Other"),
    ]
    type = models.CharField(max_length=1, choices=BANK_TYPES, default="C")
    address = models.TextField(verbose_name="Physical Address")
    telephone = models.CharField(max_length=255, blank=True, null=True, verbose_name="Telephone Numbers")
    fax = models.CharField(max_length=255, blank=True, null=True, verbose_name="Fax Numbers")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name.upper()

    class Meta:
        verbose_name = "Bank"
        verbose_name_plural = "Banks"
        ordering = ["name"]
        unique_together = ["name"]
