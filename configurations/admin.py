from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget, DateWidget, BooleanWidget
from .models import (
    Currency, Tier, Package, PackageLimit, Member, ServiceProviderType,
    ServiceProviderDocumentType, ServiceProviderTypeRequirement, ServiceProvider,
    ServiceProviderDocument, Service, ServiceTierPrice, Agent, AgentCommissionTerm,
    AgentCommission, MemberKYCRequirement, MemberKYCDocument, Vendor,
    ImportResult, ImportError, ImportSuccess
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


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('vendor_code', 'vendor_name', 'vendor_type', 'email', 'phone', 'is_active', 'created_at')
    list_filter = ('vendor_type', 'is_active', 'created_at')
    search_fields = ('vendor_code', 'vendor_name', 'email', 'tax_id')
    readonly_fields = ('vendor_code', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vendor_code', 'vendor_name', 'vendor_type', 'is_active')
        }),
        ('Linked Entity', {
            'fields': ('content_type', 'object_id'),
            'description': 'The service provider or agent this vendor represents'
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'email', 'phone')
        }),
        ('Payment Information', {
            'fields': ('preferred_payment_method', 'payment_terms_days')
        }),
        ('Tax Information', {
            'fields': ('tax_id', 'tax_rate'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('content_type', 'object_id')
        return self.readonly_fields


# Import Result Admin Classes

class ImportErrorInline(admin.TabularInline):
    model = ImportError
    extra = 0
    readonly_fields = ('row_number', 'error_type', 'field_name', 'error_message', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class ImportSuccessInline(admin.TabularInline):
    model = ImportSuccess
    extra = 0
    readonly_fields = ('row_number', 'object_id', 'object_repr', 'created_at')
    can_delete = False
    max_num = 10  # Limit display for performance
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ImportResult)
class ImportResultAdmin(admin.ModelAdmin):
    list_display = ('import_type', 'status', 'user', 'total_rows', 'successful_rows', 'failed_rows', 'success_rate', 'created_at')
    list_filter = ('import_type', 'status', 'created_at', 'user')
    search_fields = ('original_filename', 'user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'success_rate', 'duration', 'has_errors')
    inlines = [ImportErrorInline, ImportSuccessInline]
    
    fieldsets = (
        ('Import Information', {
            'fields': ('id', 'import_type', 'status', 'user', 'created_at', 'updated_at')
        }),
        ('File Information', {
            'fields': ('original_filename', 'file_format', 'file_size')
        }),
        ('Statistics', {
            'fields': ('total_rows', 'successful_rows', 'failed_rows', 'skipped_rows', 'success_rate', 'has_errors')
        }),
        ('Processing Times', {
            'fields': ('started_at', 'completed_at', 'duration'),
            'classes': ('collapse',)
        }),
        ('Options & Notes', {
            'fields': ('import_options', 'summary', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('import_type', 'user', 'original_filename', 'file_format', 'file_size', 'total_rows', 'successful_rows', 'failed_rows', 'skipped_rows', 'started_at', 'completed_at', 'import_options')
        return self.readonly_fields


@admin.register(ImportError)
class ImportErrorAdmin(admin.ModelAdmin):
    list_display = ('import_result', 'row_number', 'error_type', 'field_name', 'error_message_short', 'created_at')
    list_filter = ('error_type', 'import_result__import_type', 'created_at')
    search_fields = ('error_message', 'field_name', 'import_result__original_filename')
    readonly_fields = ('created_at',)
    
    def error_message_short(self, obj):
        return obj.error_message[:50] + "..." if len(obj.error_message) > 50 else obj.error_message
    error_message_short.short_description = 'Error Message'


@admin.register(ImportSuccess)
class ImportSuccessAdmin(admin.ModelAdmin):
    list_display = ('import_result', 'row_number', 'object_id', 'object_repr', 'created_at')
    list_filter = ('import_result__import_type', 'created_at')
    search_fields = ('object_repr', 'object_id', 'import_result__original_filename')
    readonly_fields = ('created_at',)



