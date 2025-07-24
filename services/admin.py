from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateWidget, ManyToManyWidget

from configurations.models import Service, Tier, ServiceProvider
from membership.models import Beneficiary
from services.models import (
    AdjudicationRule, AdjudicationMessageCode, AdjudicationResult,
    AdjudicationMessage, Claim, ClaimServiceLine, ServiceRequest,
    ServiceRequestItem
)


class AdjudicationRuleResource(resources.ModelResource):
    services = fields.Field(
        column_name='services',
        attribute='services',
        widget=ManyToManyWidget(Service, field='code', separator='|')
    )
    categories = fields.Field(
        column_name='categories',
        attribute='categories',
        widget=ManyToManyWidget('configurations.Service_Or_Product_Category',
                               field='name', separator='|')
    )
    provider_tiers = fields.Field(
        column_name='provider_tiers',
        attribute='provider_tiers',
        widget=ManyToManyWidget(Tier, field='name', separator='|')
    )

    class Meta:
        model = AdjudicationRule
        import_id_fields = ('name',)
        fields = ('name', 'description', 'rule_type', 'services', 'categories',
                 'min_amount', 'max_amount', 'beneficiary_type', 'member_types',
                 'provider_tiers', 'max_days_from_service', 'max_visits_per_year',
                 'max_visits_per_month', 'min_age', 'max_age', 'requires_referral',
                 'requires_prior_auth', 'requires_supporting_docs', 'action',
                 'reduction_percentage', 'reduction_amount', 'co_payment_percentage',
                 'co_payment_amount', 'priority', 'is_active', 'effective_from', 'effective_to')


class AdjudicationMessageCodeResource(resources.ModelResource):
    class Meta:
        model = AdjudicationMessageCode
        import_id_fields = ('code',)
        fields = ('code', 'title', 'description', 'message_type', 'is_visible_to_provider',
                 'is_visible_to_member', 'category', 'is_active')
        export_order = ('code', 'title', 'message_type', 'category', 'is_active')


class ClaimResource(resources.ModelResource):
    beneficiary = fields.Field(
        column_name='beneficiary_membership_dependent',
        attribute='beneficiary',
        widget=ForeignKeyWidget(Beneficiary, 'membership_number')
    )
    provider = fields.Field(
        column_name='provider_afhoz',
        attribute='provider',
        widget=ForeignKeyWidget(ServiceProvider, 'identification_no')
    )
    user = fields.Field(
        column_name='submitted_by',
        attribute='user',
        widget=ForeignKeyWidget('authentication.User', 'username')
    )

    class Meta:
        model = Claim
        import_id_fields = ('transaction_number',)
        fields = ('transaction_number', 'invoice_number', 'claimed_amount', 'accepted_amount',
                 'beneficiary_membership_dependent', 'provider_afhoz', 'whom_to_pay',
                 'status', 'start_date', 'end_date', 'submitted_by')
        export_order = ('transaction_number', 'invoice_number', 'claimed_amount',
                       'accepted_amount', 'status')


@admin.register(AdjudicationRule)
class AdjudicationRuleAdmin(ImportExportModelAdmin):
    resource_class = AdjudicationRuleResource
    list_display = ('name', 'rule_type', 'action', 'priority', 'is_active')
    list_filter = ('rule_type', 'action', 'is_active', 'beneficiary_type')
    search_fields = ('name', 'description')
    ordering = ('priority', 'name')


@admin.register(AdjudicationMessageCode)
class AdjudicationMessageCodeAdmin(ImportExportModelAdmin):
    resource_class = AdjudicationMessageCodeResource
    list_display = ('code', 'title', 'message_type', 'category', 'is_active')
    list_filter = ('message_type', 'category', 'is_active')
    search_fields = ('code', 'title', 'description')
    ordering = ('category', 'code')


@admin.register(Claim)
class ClaimAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = ClaimResource
    list_display = ('transaction_number', 'invoice_number', 'beneficiary', 'provider',
                    'claimed_amount', 'accepted_amount', 'status')
    list_filter = ('status', 'whom_to_pay', 'wellness_visit', 'created_at')
    search_fields = ('transaction_number', 'invoice_number', 'beneficiary__first_name',
                    'beneficiary__last_name', 'provider__name')
    readonly_fields = ('transaction_number',)
    date_hierarchy = 'created_at'
