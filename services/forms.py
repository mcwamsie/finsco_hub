from django import forms
from django.forms import inlineformset_factory

from .models.claim import Claim, ClaimServiceLine
from .models.service_request import ServiceRequest, ServiceRequestItem
from configurations.models.service import Service
from configurations.models.service_provider import ServiceProvider
from membership.models import Beneficiary


class ClaimForm(forms.ModelForm):
    """Form for creating and updating claims"""
    
    class Meta:
        model = Claim
        fields = [
            'invoice_number', 'claimed_amount', 'beneficiary', 'provider',
            'service_request', 'referring_provider_number', 'referring_provider_name',
            'whom_to_pay', 'start_date', 'end_date'
        ]
        widgets = {
            'invoice_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Enter invoice number'
            }),
            'claimed_amount': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'beneficiary': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'provider': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'service_request': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'referring_provider_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Referring provider number'
            }),
            'referring_provider_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'Referring provider name'
            }),
            'whom_to_pay': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficiary'].queryset = Beneficiary.objects.filter(status='A')
        self.fields['provider'].queryset = ServiceProvider.objects.filter(status='A')
        self.fields['service_request'].queryset = ServiceRequest.objects.filter(status__in=['A', 'P'])
        self.fields['service_request'].required = False


class ClaimServiceLineForm(forms.ModelForm):
    """Form for claim service lines"""
    
    class Meta:
        model = ClaimServiceLine
        fields = [
            'service', 'service_date', 'unit_price', 'quantity',
            'claimed_amount'
        ]
        widgets = {
            'service': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'service_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'claimed_amount': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = Service.objects.filter(is_active=True)


class ServiceRequestForm(forms.ModelForm):
    """Form for creating and updating service requests"""
    
    class Meta:
        model = ServiceRequest
        fields = [
            'beneficiary', 'service_provider', 'referring_provider',
            'priority', 'chief_complaint', 'clinical_history',
            'planned_treatment', 'estimated_amount'
        ]
        widgets = {
            'beneficiary': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'service_provider': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'referring_provider': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'priority': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'chief_complaint': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Describe the chief complaint'
            }),
            'clinical_history': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Provide clinical history'
            }),
            'planned_treatment': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Describe planned treatment'
            }),
            'estimated_amount': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficiary'].queryset = Beneficiary.objects.filter(status='A')
        self.fields['service_provider'].queryset = ServiceProvider.objects.filter(status='A')
        self.fields['referring_provider'].queryset = ServiceProvider.objects.filter(status='A')
        self.fields['referring_provider'].required = False


class ServiceRequestItemForm(forms.ModelForm):
    """Form for service request items"""
    
    class Meta:
        model = ServiceRequestItem
        fields = [
            'service', 'quantity', 'unit_price', 'estimated_amount',
            'clinical_justification'
        ]
        widgets = {
            'service': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'estimated_amount': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'clinical_justification': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Provide clinical justification'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = Service.objects.filter(is_active=True)


class ServiceForm(forms.ModelForm):
    """Form for creating and updating services"""
    
    class Meta:
        model = Service
        fields = [
            'code', 'description', 'service_provider_type', 'unit_of_measure',
            'base_price', 'is_active', 'requires_authorization', 'requires_referral',
            'is_emergency_service'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter service code'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter service description'
            }),
            'service_provider_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'unit_of_measure': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Each, Session, Hour'
            }),
            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'requires_authorization': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'requires_referral': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_emergency_service': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# Inline formsets for related models
ClaimServiceLineFormSet = inlineformset_factory(
    Claim, ClaimServiceLine, form=ClaimServiceLineForm, extra=1, can_delete=True
)

ServiceRequestItemFormSet = inlineformset_factory(
    ServiceRequest, ServiceRequestItem, form=ServiceRequestItemForm, extra=1, can_delete=True
)