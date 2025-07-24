from django.db import models

from configurations.models.base_model import BaseModel


class Currency(BaseModel):
    code = models.CharField(max_length=3, unique=True, verbose_name="Currency Code")
    name = models.CharField(max_length=100, verbose_name="Currency Name")
    symbol = models.CharField(max_length=5, verbose_name="Currency Symbol")
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, default=1.0, verbose_name="Exchange Rate to Base Currency")
    is_base_currency = models.BooleanField(default=False, verbose_name="Is Base Currency")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ["code"]
