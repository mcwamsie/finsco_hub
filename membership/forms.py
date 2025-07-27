from django import forms
from django.core.exceptions import ValidationError

from configurations.models import Member
from membership.models import Beneficiary, TopUp


class MemberForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Update parent field to include all valid parent types (Community, Family, Corporate)
        self.fields['parent'] = forms.ModelChoiceField(
            queryset=Member.objects.valid_parents(),
            required=False,
            help_text="Only Community, Family, or Corporate members can be parents"
        )
        
        # Add help text for type field
        self.fields['type'].help_text = (
            "Individual and HealthSave members must have a parent. "
            "Community, Family, and Corporate members can be standalone or have children."
        )

    def clean(self):
        cleaned_data = super().clean()
        member_type = cleaned_data.get('type')
        parent = cleaned_data.get('parent')
        
        # Validate member hierarchy rules
        # if member_type in ['IN', 'HS']:  # Individual or HealthSave
        #     if not parent:
        #         raise ValidationError({
        #             'parent': f'{dict(Member.MEMBER_TYPES)[member_type]} members must have a parent. Only Community, Family, or Corporate members can be standalone.'
        #         })
        
        if parent:
            if member_type not in ['IN', 'HS']:
                raise ValidationError({
                    'parent': f'{dict(Member.MEMBER_TYPES)[member_type]} members cannot be child members. Only Individual or HealthSave members can be children.'
                })
            
            if parent.type not in ['CM', 'FM', 'CO']:
                raise ValidationError({
                    'parent': f'Parent must be a Community, Family, or Corporate member. {parent.get_type_display()} cannot be a parent.'
                })
        
        return cleaned_data

    class Meta:
        model = Member
        fields = [
            'name', 'type', 'alias', 'currency', 'address_line_1', 'address_line_2',
            'address_line_3', 'mobile', 'telephone', 'email', 'signing_rule',
      'sponsor', 'default_package', 'parent', 'logo', 'registered_by'
        ]


class BeneficiaryForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text for type field
        self.fields['type'].help_text = (
            "Principal: Main member, Spouse: Married partner, "
            "Dependent: Child/Dependent, Employee: For corporate members"
        )
        
        # Add help text for relationship field
        self.fields['relationship'].help_text = (
            "Specify the relationship to the principal member"
        )

    def clean(self):
        cleaned_data = super().clean()
        member = cleaned_data.get('member')
        beneficiary_type = cleaned_data.get('type')
        national_id = cleaned_data.get('national_id_number')
        
        # Validate that only one principal beneficiary exists per member
        if beneficiary_type == 'P':
            existing_principal = Beneficiary.objects.filter(
                member=member, type='P'
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_principal.exists():
                raise ValidationError({
                    'type': 'This member already has a principal beneficiary.'
                })
        
        # Validate unique national ID per member
        if national_id and member:
            existing_beneficiary = Beneficiary.objects.filter(
                member=member, national_id_number=national_id
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_beneficiary.exists():
                raise ValidationError({
                    'national_id_number': 'A beneficiary with this National ID already exists for this member.'
                })
        
        return cleaned_data

    class Meta:
        model = Beneficiary
        fields = [
            'first_name', 'last_name', 'middle_name', 'photo', 'national_id_number', 
            'date_of_birth', 'gender', 'mobile', 'email', 'physical_address',
            'member', 'relationship', 'status', 'type',
            # 'package', 'annual_limit',
            'benefit_start_date', 'principal', 'other_identity_number'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'benefit_start_date': forms.DateInput(attrs={'type': 'date'}),
            'physical_address': forms.Textarea(attrs={'rows': 3}),
        }


class TopUpForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text for amount field
        self.fields['amount'].help_text = (
            "Enter the top-up amount. Admin fee will be calculated automatically."
        )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError('Top-up amount must be greater than zero.')
        return amount

    class Meta:
        model = TopUp
        fields = [
            'member', 'account', 'amount', 'photo', 'mobile_number', 
            'mobile_network', 'bank_reference', 'payment_method'
        ]
        widgets = {
            'photo': forms.FileInput(attrs={'accept': 'image/*'}),
            'mobile_number': forms.TextInput(attrs={'placeholder': '+1234567890'}),
            'bank_reference': forms.TextInput(attrs={'placeholder': 'Bank reference number'}),
        }
