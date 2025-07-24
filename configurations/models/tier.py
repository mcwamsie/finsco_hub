from django.db import models

from configurations.models.base_model import BaseModel


class Tier(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Tier Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    level = models.PositiveIntegerField(verbose_name="Tier Level")
    requirements = models.TextField(blank=True, null=True, verbose_name="Requirements")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    def __str__(self):
        return f"Tier {self.level}: {self.name}"

    class Meta:
        verbose_name = "Tier"
        verbose_name_plural = "Tiers"
        ordering = ["level"]
        unique_together = [("level",)]
