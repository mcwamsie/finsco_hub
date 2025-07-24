from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget, DateWidget, BooleanWidget
from .models import (
    Currency, Tier, Package, PackageLimit, Member, ServiceProviderType,
    ServiceProviderDocumentType, ServiceProviderTypeRequirement, ServiceProvider,
    ServiceProviderDocument, Service, ServiceTierPrice, Agent, AgentCommissionTerm,
    AgentCommission, MemberKYCRequirement, MemberKYCDocument
)
from .resources import ValidatedMemberResource, CurrencyResource, AgentCommissionResource, AgentCommissionTermResource, \
    TierResource, PackageResource, PackageLimitResource, ServiceProviderTypeResource, \
    ServiceProviderDocumentTypeResource, ServiceProviderTypeRequirementResource, ServiceProviderResource, \
    ServiceResource, ServiceTierPriceResource, AgentResource, MemberKYCRequirementResource, MemberKYCDocumentResource


# Currency Resources


@admin.register(Currency)
class CurrencyAdmin(ImportExportModelAdmin):
    resource_class = CurrencyResource
    list_display = ('code', 'name', 'symbol', 'exchange_rate', 'is_base_currency', 'is_active')
    list_filter = ('is_base_currency', 'is_active')
    search_fields = ('code', 'name')



@admin.register(Tier)
class TierAdmin(ImportExportModelAdmin):
    resource_class = TierResource
    list_display = ('level', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('level',)



@admin.register(Package)
class PackageAdmin(ImportExportModelAdmin):
    resource_class = PackageResource
    list_display = ('name', 'global_annual_limit', 'monthly_contribution', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


@admin.register(PackageLimit)
class PackageLimitAdmin(ImportExportModelAdmin):
    resource_class = PackageLimitResource
    list_display = ('package', 'service_provider_type', 'annual_limit', 'per_visit_limit')
    list_filter = ('package', 'service_provider_type')




@admin.register(Member)
class MemberAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = ValidatedMemberResource
    list_display = ('membership_number', 'name', 'type', 'status', 'currency', 'date_joined')
    list_filter = ('type', 'status', 'currency', 'date_joined')
    search_fields = ('membership_number', 'name', 'email', 'mobile')
    readonly_fields = ('membership_number',)


@admin.register(ServiceProviderType)
class ServiceProviderTypeAdmin(ImportExportModelAdmin):
    resource_class = ServiceProviderTypeResource
    list_display = ('name', 'requires_license', 'is_active')
    list_filter = ('requires_license', 'is_active')


@admin.register(ServiceProviderDocumentType)
class ServiceProviderDocumentTypeAdmin(ImportExportModelAdmin):
    resource_class = ServiceProviderDocumentTypeResource
    list_display = ('name', 'is_mandatory', 'has_expiry_date', 'reminder_days_before_expiry')
    list_filter = ('is_mandatory', 'has_expiry_date')


@admin.register(ServiceProviderTypeRequirement)
class ServiceProviderTypeRequirementAdmin(ImportExportModelAdmin):
    resource_class = ServiceProviderTypeRequirementResource
    list_display = ('provider_type', 'document_type', 'is_required', 'withhold_payment_if_missing')


@admin.register(ServiceProvider)
class ServiceProviderAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = ServiceProviderResource
    list_display = ('account_no', 'identification_no', 'name', 'type', 'tier', 'status')
    list_filter = ('type', 'tier', 'status', 'is_from_network', 'is_third_party')
    search_fields = ('account_no', 'identification_no', 'name', 'email')
    readonly_fields = ('account_no',)


@admin.register(Service)
class ServiceAdmin(ImportExportModelAdmin):
    resource_class = ServiceResource
    list_display = ('code', 'description', 'service_provider_type', 'base_price', 'is_active')
    list_filter = ('service_provider_type', 'is_active', 'requires_authorization', 'requires_referral')
    search_fields = ('code', 'description')


@admin.register(ServiceTierPrice)
class ServiceTierPriceAdmin(ImportExportModelAdmin):
    resource_class = ServiceTierPriceResource
    list_display = ('service', 'tier', 'highest_amount_paid', 'recommended_price', 'effective_from')
    list_filter = ('tier', 'effective_from')


@admin.register(Agent)
class AgentAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = AgentResource
    list_display = ('account_no', 'name', 'type', 'base_commission_rate', 'status')
    list_filter = ('type', 'status', 'currency')
    search_fields = ('account_no', 'name', 'email', 'mobile')
    readonly_fields = ('account_no',)


@admin.register(AgentCommissionTerm)
class AgentCommissionTermAdmin(ImportExportModelAdmin):
    resource_class = AgentCommissionTermResource
    list_display = ('agent', 'name', 'condition_type', 'threshold_value', 'reward_type', 'is_active')
    list_filter = ('condition_type', 'reward_type', 'is_active')


@admin.register(AgentCommission)
class AgentCommissionAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = AgentCommissionResource
    list_display = ('commission_number', 'agent', 'commission_type', 'commission_amount', 'status')
    list_filter = ('commission_type', 'status', 'period_from')
    search_fields = ('commission_number', 'agent__name')
    readonly_fields = ('commission_number',)



@admin.register(MemberKYCRequirement)
class MemberKYCRequirementAdmin(ImportExportModelAdmin):
    resource_class = MemberKYCRequirementResource
    list_display = ('name', 'requirement_type', 'is_mandatory', 'has_expiry', 'is_active')
    list_filter = ('requirement_type', 'is_mandatory', 'has_expiry', 'is_active')
    ordering = ('sort_order', 'name')


@admin.register(MemberKYCDocument)
class MemberKYCDocumentAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = MemberKYCDocumentResource
    list_display = ('member', 'requirement', 'status', 'issue_date', 'expiry_date')
    list_filter = ('requirement', 'status', 'verified_at')
    search_fields = ('member__membership_number', 'member__name', 'document_number')



