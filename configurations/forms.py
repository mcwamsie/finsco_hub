from django import forms
from import_export.forms import ImportForm, ExportForm


class MemberImportForm(ImportForm):
    validate_membership_numbers = forms.BooleanField(
        required=False,
        initial=True,
        label="Validate membership number format"
    )
    auto_generate_missing = forms.BooleanField(
        required=False,
        initial=False,
        label="Auto-generate missing membership numbers"
    )
    skip_duplicates = forms.BooleanField(
        required=False,
        initial=True,
        label="Skip duplicate membership numbers"
    )


class BeneficiaryImportForm(ImportForm):
    validate_age_limits = forms.BooleanField(
        required=False,
        initial=True,
        label="Validate age limits for dependents"
    )
    auto_assign_dependent_codes = forms.BooleanField(
        required=False,
        initial=True,
        label="Auto-assign dependent codes"
    )


class ServiceProviderImportForm(ImportForm):
    validate_afhoz_numbers = forms.BooleanField(
        required=False,
        initial=True,
        label="Validate AFHOZ number format"
    )
    check_existing_providers = forms.BooleanField(
        required=False,
        initial=True,
        label="Check for existing providers"
    )
