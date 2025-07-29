from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from .base_model import BaseModel


class Vendor(BaseModel):
    """
    Unified model for all vendors (Service Providers and Agents)
    """
    # Vendor Identification
    vendor_code = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Vendor Code"
    )
    vendor_name = models.CharField(
        max_length=255, 
        verbose_name="Vendor Name"
    )
    
    # Vendor Type
    VENDOR_TYPES = [
        ("SP", "Service Provider"),
        ("AG", "Agent"),
    ]
    vendor_type = models.CharField(
        max_length=2, 
        choices=VENDOR_TYPES,
        verbose_name="Vendor Type"
    )
    
    # Generic Foreign Key to link to either ServiceProvider or Agent
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ('serviceprovider', 'agent')}
    )
    object_id = models.UUIDField()
    vendor_object = GenericForeignKey('content_type', 'object_id')
    
    # Contact Information
    contact_person = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Contact Person"
    )
    email = models.EmailField(
        blank=True, 
        null=True,
        verbose_name="Email Address"
    )
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name="Phone Number"
    )
    
    # Payment Information
    preferred_payment_method = models.ForeignKey(
        'PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_vendors",
        verbose_name="Preferred Payment Method"
    )
    
    # Tax Information
    tax_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Tax ID"
    )
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name="Tax Rate (%)"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active"
    )
    
    # Payment Terms
    payment_terms_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Payment Terms (Days)"
    )
    
    def save(self, *args, **kwargs):
        if not self.vendor_code:
            # Auto-generate vendor code based on type
            if self.vendor_type == 'SP':
                prefix = 'SP'
            else:
                prefix = 'AG'
            
            # Get the next sequence number
            from sequences import Sequence
            sequence_number = Sequence(f"vendor_{self.vendor_type}").get_next_value()
            self.vendor_code = f"{prefix}{sequence_number:06d}"
        
        # Auto-populate vendor name from linked object
        if self.vendor_object:
            if hasattr(self.vendor_object, 'name'):
                self.vendor_name = self.vendor_object.name
            elif hasattr(self.vendor_object, 'first_name') and hasattr(self.vendor_object, 'last_name'):
                self.vendor_name = f"{self.vendor_object.first_name} {self.vendor_object.last_name}"
        
        super().save(*args, **kwargs)
    
    @property
    def service_provider(self):
        """Get the service provider if this vendor is a service provider"""
        if self.vendor_type == 'SP' and self.content_type.model == 'serviceprovider':
            return self.vendor_object
        return None
    
    @property
    def agent(self):
        """Get the agent if this vendor is an agent"""
        if self.vendor_type == 'AG' and self.content_type.model == 'agent':
            return self.vendor_object
        return None
    
    def __str__(self):
        return f"{self.vendor_code} - {self.vendor_name}"
    
    class Meta:
        ordering = ['vendor_code']
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
        unique_together = ['content_type', 'object_id']