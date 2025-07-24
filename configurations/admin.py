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


# Currency Resources
class CurrencyResource(resources.ModelResource):
    class Meta:
        model = Currency
        import_id_fields = ('code',)
        fields = ('code', 'name', 'symbol', 'exchange_rate', 'is_base_currency', 'is_active')
        export_order = ('code', 'name', 'symbol', 'exchange_rate', 'is_base_currency', 'is_active')


@admin.register(Currency)
class CurrencyAdmin(ImportExportModelAdmin):
    resource_class = CurrencyResource
    list_display = ('code', 'name', 'symbol', 'exchange_rate', 'is_base_currency', 'is_active')
    list_filter = ('is_base_currency', 'is_active')
    search_fields = ('code', 'name')


# Tier Resources
class TierResource(resources.ModelResource):
    class Meta:
        model = Tier
        import_id_fields = ('level',)
        fields = ('level', 'name', 'description', 'requirements', 'is_active')
        export_order = ('level', 'name', 'description', 'requirements', 'is_active')


@admin.register(Tier)
class TierAdmin(ImportExportModelAdmin):
    resource_class = TierResource
    list_display = ('level', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('level',)


# Package Resources
class PackageResource(resources.ModelResource):
    class Meta:
        model = Package
        import_id_fields = ('name',)
        fields = ('name', 'description', 'global_annual_limit', 'global_family_limit',
                 'monthly_contribution', 'child_monthly_contribution', 'is_active')
        export_order = ('name', 'description', 'global_annual_limit', 'global_family_limit',
                       'monthly_contribution', 'child_monthly_contribution', 'is_active')


class PackageLimitResource(resources.ModelResource):
    package = fields.Field(
        column_name='package',
        attribute='package',
        widget=ForeignKeyWidget(Package, 'name')
    )
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget('configurations.Service_Or_Product_Category', 'name')
    )

    class Meta:
        model = PackageLimit
        import_id_fields = ('package', 'category')
        fields = ('package', 'category', 'annual_limit', 'per_visit_limit', 'max_visits_per_year',
                 'co_payment_percentage', 'co_payment_amount', 'waiting_period_days')


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


# Member Resources
class MemberResource(resources.ModelResource):
    currency = fields.Field(
        column_name='currency',
        attribute='currency',
        widget=ForeignKeyWidget(Currency, 'code')
    )
    default_package = fields.Field(
        column_name='default_package',
        attribute='default_package',
        widget=ForeignKeyWidget(Package, 'name')
    )
    parent = fields.Field(
        column_name='parent_membership_number',
        attribute='parent',
        widget=ForeignKeyWidget(Member, 'membership_number')
    )
    registered_by = fields.Field(
        column_name='registered_by_agent',
        attribute='registered_by',
        widget=ForeignKeyWidget(Agent, 'account_no')
    )
    date_joined = fields.Field(
        column_name='date_joined',
        attribute='date_joined',
        widget=DateWidget(format='%Y-%m-%d')
    )

    class Meta:
        model = Member
        import_id_fields = ('membership_number',)
        fields = ('membership_number', 'name', 'type', 'alias', 'currency', 'address_line_1',
                 'address_line_2', 'address_line_3', 'mobile', 'telephone', 'email',
                 'signing_rule', 'status', 'sponsor', 'date_joined', 'stop_order_form',
                 'stop_order_amount', 'stop_order_number', 'global_annual_limit',
                 'parent_membership_number', 'default_package', 'registered_by_agent')
        export_order = ('membership_number', 'name', 'type', 'status', 'currency',
                       'mobile', 'email', 'date_joined', 'registered_by_agent')

    def before_import_row(self, row, **kwargs):
        # Custom validation before importing
        if row.get('type') and row['type'] not in dict(Member.MEMBER_TYPES):
            raise ValueError(f"Invalid member type: {row['type']}")


@admin.register(Member)
class MemberAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = MemberResource
    list_display = ('membership_number', 'name', 'type', 'status', 'currency', 'date_joined')
    list_filter = ('type', 'status', 'currency', 'date_joined')
    search_fields = ('membership_number', 'name', 'email', 'mobile')
    readonly_fields = ('membership_number',)


# Service Provider Type Resources
class ServiceProviderTypeResource(resources.ModelResource):
    class Meta:
        model = ServiceProviderType
        import_id_fields = ('name',)
        fields = ('name', 'description', 'requires_license', 'is_active')


class ServiceProviderDocumentTypeResource(resources.ModelResource):
    class Meta:
        model = ServiceProviderDocumentType
        import_id_fields = ('name',)
        fields = ('name', 'description', 'is_mandatory', 'has_expiry_date', 'reminder_days_before_expiry')


class ServiceProviderTypeRequirementResource(resources.ModelResource):
    provider_type = fields.Field(
        column_name='provider_type',
        attribute='provider_type',
        widget=ForeignKeyWidget(ServiceProviderType, 'name')
    )
    document_type = fields.Field(
        column_name='document_type',
        attribute='document_type',
        widget=ForeignKeyWidget(ServiceProviderDocumentType, 'name')
    )

    class Meta:
        model = ServiceProviderTypeRequirement
        import_id_fields = ('provider_type', 'document_type')
        fields = ('provider_type', 'document_type', 'is_required', 'withhold_payment_if_missing',
                 'withhold_payment_if_expired', 'withhold_percentage', 'withhold_fixed_amount')


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


# Service Provider Resources
class ServiceProviderResource(resources.ModelResource):
    tier = fields.Field(
        column_name='tier',
        attribute='tier',
        widget=ForeignKeyWidget(Tier, 'name')
    )
    type = fields.Field(
        column_name='type',
        attribute='type',
        widget=ForeignKeyWidget(ServiceProviderType, 'name')
    )
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget('configurations.Service_Or_Product_Category', 'name')
    )
    region = fields.Field(
        column_name='region',
        attribute='region',
        widget=ForeignKeyWidget('configurations.Region', 'name')
    )
    parent = fields.Field(
        column_name='parent_provider',
        attribute='parent',
        widget=ForeignKeyWidget(ServiceProvider, 'account_no')
    )

    class Meta:
        model = ServiceProvider
        import_id_fields = ('identification_no',)
        fields = ('account_no', 'name', 'alias', 'identification_no', 'address_line_1',
                 'address_line_2', 'address_line_3', 'mobile', 'telephone', 'email',
                 'tier', 'type', 'category', 'signing_rule', 'status', 'bp_number',
                 'region', 'council_number', 'hpa_number', 'is_from_network',
                 'is_third_party', 'parent_provider')
        export_order = ('account_no', 'identification_no', 'name', 'type', 'tier',
                       'status', 'mobile', 'email')

    def before_import_row(self, row, **kwargs):
        # Validate status choices
        if row.get('status') and row['status'] not in ['A', 'I', 'S']:
            raise ValueError(f"Invalid status: {row['status']}")


@admin.register(ServiceProvider)
class ServiceProviderAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = ServiceProviderResource
    list_display = ('account_no', 'identification_no', 'name', 'type', 'tier', 'status')
    list_filter = ('type', 'tier', 'status', 'is_from_network', 'is_third_party')
    search_fields = ('account_no', 'identification_no', 'name', 'email')
    readonly_fields = ('account_no',)


# Service Resources
class ServiceResource(resources.ModelResource):
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget('configurations.Service_Or_Product_Category', 'name')
    )

    class Meta:
        model = Service
        import_id_fields = ('code',)
        fields = ('code', 'description', 'category', 'unit_of_measure', 'base_price',
                 'is_active', 'requires_authorization', 'requires_referral', 'is_emergency_service')
        export_order = ('code', 'description', 'category', 'base_price', 'is_active')


class ServiceTierPriceResource(resources.ModelResource):
    service = fields.Field(
        column_name='service_code',
        attribute='service',
        widget=ForeignKeyWidget(Service, 'code')
    )
    tier = fields.Field(
        column_name='tier',
        attribute='tier',
        widget=ForeignKeyWidget(Tier, 'name')
    )
    effective_from = fields.Field(
        column_name='effective_from',
        attribute='effective_from',
        widget=DateWidget(format='%Y-%m-%d')
    )
    effective_to = fields.Field(
        column_name='effective_to',
        attribute='effective_to',
        widget=DateWidget(format='%Y-%m-%d')
    )

    class Meta:
        model = ServiceTierPrice
        import_id_fields = ('service', 'tier', 'effective_from')
        fields = ('service_code', 'tier', 'highest_amount_paid', 'recommended_price',
                 'max_payable_amount', 'effective_from', 'effective_to')


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


# Agent Resources
class AgentResource(resources.ModelResource):
    region = fields.Field(
        column_name='region',
        attribute='region',
        widget=ForeignKeyWidget('configurations.Region', 'name')
    )
    currency = fields.Field(
        column_name='currency',
        attribute='currency',
        widget=ForeignKeyWidget(Currency, 'code')
    )

    class Meta:
        model = Agent
        import_id_fields = ('account_no',)
        fields = ('account_no', 'name', 'alias', 'identification_no', 'address_line_1',
                 'address_line_2', 'address_line_3', 'mobile', 'telephone', 'email',
                 'type', 'base_commission_rate', 'status', 'region', 'currency')
        export_order = ('account_no', 'name', 'type', 'status', 'base_commission_rate',
                       'mobile', 'email')


class AgentCommissionTermResource(resources.ModelResource):
    agent = fields.Field(
        column_name='agent_account_no',
        attribute='agent',
        widget=ForeignKeyWidget(Agent, 'account_no')
    )
    effective_from = fields.Field(
        column_name='effective_from',
        attribute='effective_from',
        widget=DateWidget(format='%Y-%m-%d')
    )
    effective_to = fields.Field(
        column_name='effective_to',
        attribute='effective_to',
        widget=DateWidget(format='%Y-%m-%d')
    )

    class Meta:
        model = AgentCommissionTerm
        fields = ('agent_account_no', 'name', 'description', 'condition_type', 'threshold_value',
                 'member_types', 'period_days', 'reward_type', 'reward_percentage',
                 'reward_fixed_amount', 'is_active', 'effective_from', 'effective_to', 'priority')


class AgentCommissionResource(resources.ModelResource):
    agent = fields.Field(
        column_name='agent_account_no',
        attribute='agent',
        widget=ForeignKeyWidget(Agent, 'account_no')
    )
    commission_term = fields.Field(
        column_name='commission_term',
        attribute='commission_term',
        widget=ForeignKeyWidget(AgentCommissionTerm, 'name')
    )
    member = fields.Field(
        column_name='member_number',
        attribute='member',
        widget=ForeignKeyWidget(Member, 'membership_number')
    )

    class Meta:
        model = AgentCommission
        import_id_fields = ('commission_number',)
        fields = ('commission_number', 'agent_account_no', 'commission_term', 'member_number',
                 'commission_type', 'base_amount', 'commission_rate', 'commission_amount',
                 'period_from', 'period_to', 'status')
        export_order = ('commission_number', 'agent_account_no', 'commission_type',
                       'commission_amount', 'status')


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


# KYC Resources
class MemberKYCRequirementResource(resources.ModelResource):
    class Meta:
        model = MemberKYCRequirement
        import_id_fields = ('name',)
        fields = ('name', 'description', 'requirement_type', 'member_types', 'is_mandatory',
                 'accepted_file_types', 'max_file_size_mb', 'has_expiry',
                 'requires_manual_verification', 'is_active', 'sort_order')


class MemberKYCDocumentResource(resources.ModelResource):
    member = fields.Field(
        column_name='member_number',
        attribute='member',
        widget=ForeignKeyWidget(Member, 'membership_number')
    )
    requirement = fields.Field(
        column_name='requirement',
        attribute='requirement',
        widget=ForeignKeyWidget(MemberKYCRequirement, 'name')
    )
    verified_by = fields.Field(
        column_name='verified_by',
        attribute='verified_by',
        widget=ForeignKeyWidget('authentication.User', 'username')
    )

    class Meta:
        model = MemberKYCDocument
        fields = ('member_number', 'requirement', 'document_number', 'issue_date',
                 'expiry_date', 'issuing_authority', 'status', 'verified_by', 'verified_at',
                 'rejection_reason', 'notes')


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



