import secrets

from django.contrib.auth.hashers import make_password
from django.db import models

from configurations.models.base_model import BaseModel


class RegisteredApplication(BaseModel):
    name = models.CharField(max_length=100)
    secret = models.TextField(blank=True, editable=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.secret:
            token = secrets.token_hex(32)
            print("token", token)
            self.secret = make_password(token)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Registered Applications'
        verbose_name = 'Registered Application'
        ordering = ['name']
        unique_together = ('name',)
