from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from accounting.models import (
    MemberAccount, MemberTransaction, PaymentMethodAccount, PaymentMethodTransaction,
    AgentAccount, AgentTransaction, ProviderAccount, ProviderTransaction, PaymentMethodTransfer
)
# from accounts.models import (
#     MemberAccount, ProviderAccount, MemberTransaction, ProviderTransaction,
#     TopUp, TopUpProcessing
# )

from configurations.models import Member, Currency
from membership.models import TopUp


class MemberAccountResource(resources.ModelResource):
    member = fields.Field(
        column_name='member_number',
        attribute='member',
        widget=ForeignKeyWidget(Member, 'membership_number')
    )
    currency = fields.Field(
        column_name='currency',
        attribute='currency',
        widget=ForeignKeyWidget(Currency, 'code')
    )
    parent_account = fields.Field(
        column_name='parent_account_member',
        attribute='parent_account',
        widget=ForeignKeyWidget(MemberAccount, 'member__membership_number')
    )

    class Meta:
        model = MemberAccount
        import_id_fields = ('member', 'currency')
        fields = ('member_number', 'currency', 'balance', 'available_balance',
                 'reserved_balance', 'credit_limit', 'overdraft_limit', 'status',
                 'interest_rate', 'monthly_fee', 'parent_account_member')
        export_order = ('member_number', 'currency', 'balance', 'available_balance', 'status')


class TopUpResource(resources.ModelResource):
    member = fields.Field(
        column_name='member_number',
        attribute='member',
        widget=ForeignKeyWidget(Member, 'membership_number')
    )

    class Meta:
        model = TopUp
        import_id_fields = ('top_up_number',)
        fields = ('top_up_number', 'member_number', 'amount', 'net_amount',
                 'status', 'mobile_number', 'bank_reference', 'photo')
        export_order = ('top_up_number', 'member_number', 'amount', 'status', 'request_date')


@admin.register(MemberAccount)
class MemberAccountAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = MemberAccountResource
    list_display = ('member', 'currency', 'balance', 'available_balance', 'status')
    list_filter = ('currency', 'status')
    search_fields = ('member__membership_number', 'member__name')


@admin.register(PaymentMethodAccount)
class PaymentMethodAccountAdmin(admin.ModelAdmin):
    list_display = ('payment_method', 'currency', 'current_balance', 'available_balance', 'status')
    list_filter = ('currency', 'status', 'payment_method__type')
    search_fields = ('payment_method__name',)
    readonly_fields = ('total_debited', 'total_credited', 'total_processing_fees', 'last_reconciled_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('payment_method', 'currency', 'status')
        }),
        ('Balances', {
            'fields': ('current_balance', 'available_balance', 'pending_balance')
        }),
        ('Cumulative Totals', {
            'fields': ('total_debited', 'total_credited', 'total_processing_fees'),
            'classes': ('collapse',)
        }),
        ('Limits', {
            'fields': ('daily_transaction_limit', 'monthly_transaction_limit'),
            'classes': ('collapse',)
        }),
        ('Reconciliation', {
            'fields': ('last_reconciled_at', 'reconciliation_variance'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentMethodTransaction)
class PaymentMethodTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_number', 'account', 'transaction_type', 'debited_amount', 'credited_amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'account__payment_method', 'created_at')
    search_fields = ('transaction_number', 'reference_number', 'external_reference')
    readonly_fields = ('transaction_number', 'balance_after', 'available_balance_after', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_number', 'account', 'transaction_type', 'status')
        }),
        ('Amounts', {
            'fields': ('debited_amount', 'credited_amount', 'processing_fee')
        }),
        ('Balances After', {
            'fields': ('balance_after', 'available_balance_after'),
            'classes': ('collapse',)
        }),
        ('References', {
            'fields': ('description', 'reference_number', 'external_reference')
        }),
        ('Gateway Information', {
            'fields': ('gateway_transaction_id', 'gateway_response_code', 'gateway_response_message'),
            'classes': ('collapse',)
        }),
        ('Related Records', {
            'fields': ('member_transaction', 'provider_transaction', 'agent_transaction', 'vendor'),
            'classes': ('collapse',)
        }),
        ('Processing', {
            'fields': ('processed_by', 'processed_at', 'settlement_date', 'settlement_reference'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AgentAccount)
class AgentAccountAdmin(admin.ModelAdmin):
    list_display = ('agent', 'currency', 'current_balance', 'commission_balance', 'status', 'last_payout_date')
    list_filter = ('currency', 'status', 'payout_frequency', 'agent__type')
    search_fields = ('agent__name', 'agent__account_no')
    readonly_fields = ('total_commissions_earned', 'total_commissions_paid', 'total_debited', 'total_credited', 'commission_balance', 'is_eligible_for_payout')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('agent', 'currency', 'status')
        }),
        ('Balances', {
            'fields': ('current_balance', 'available_balance', 'pending_balance')
        }),
        ('Commission Tracking', {
            'fields': ('total_commissions_earned', 'total_commissions_paid', 'pending_commissions', 'commission_balance', 'is_eligible_for_payout')
        }),
        ('Cumulative Totals', {
            'fields': ('total_debited', 'total_credited', 'total_withholding', 'total_deductions'),
            'classes': ('collapse',)
        }),
        ('Payment Settings', {
            'fields': ('minimum_payout_amount', 'payout_frequency', 'preferred_payment_method')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'bank_account_number', 'bank_routing_number', 'bank_account_name'),
            'classes': ('collapse',)
        }),
        ('Tax Information', {
            'fields': ('tax_id_number', 'withholding_tax_rate'),
            'classes': ('collapse',)
        }),
        ('Payout History', {
            'fields': ('last_payout_date', 'last_payout_amount', 'next_payout_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AgentTransaction)
class AgentTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_number', 'account', 'transaction_type', 'credited_amount', 'debited_amount', 'net_amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'account__agent', 'created_at', 'tax_year')
    search_fields = ('transaction_number', 'reference_number', 'account__agent__name')
    readonly_fields = ('transaction_number', 'net_amount', 'balance_after', 'commission_balance_after', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('transaction_number', 'account', 'transaction_type', 'status')
        }),
        ('Amounts', {
            'fields': ('debited_amount', 'credited_amount', 'withholding_amount', 'deduction_amount', 'net_amount')
        }),
        ('Balances After', {
            'fields': ('balance_after', 'commission_balance_after'),
            'classes': ('collapse',)
        }),
        ('Description & References', {
            'fields': ('description', 'reference_number')
        }),
        ('Commission Period', {
            'fields': ('commission_period_from', 'commission_period_to'),
            'classes': ('collapse',)
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_reference', 'payment_date'),
            'classes': ('collapse',)
        }),
        ('Related Records', {
            'fields': ('agent_commission', 'member_transaction'),
            'classes': ('collapse',)
        }),
        ('Processing', {
            'fields': ('processed_by', 'processed_at', 'approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        ('Tax Information', {
            'fields': ('tax_year', 'tax_period'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentMethodTransfer)
class PaymentMethodTransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_number', 'from_account', 'to_account', 'amount', 'transfer_type', 'status', 'created_at')
    list_filter = ('transfer_type', 'status', 'from_account__payment_method', 'to_account__payment_method', 'created_at')
    search_fields = ('transfer_number', 'reference', 'description')
    readonly_fields = ('transfer_number', 'from_transaction', 'to_transaction', 'processed_at', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transfer Details', {
            'fields': ('transfer_number', 'transfer_type', 'status')
        }),
        ('Accounts', {
            'fields': ('from_account', 'to_account')
        }),
        ('Amounts', {
            'fields': ('amount', 'transfer_fee')
        }),
        ('Description & References', {
            'fields': ('description', 'reference')
        }),
        ('Related Transactions', {
            'fields': ('from_transaction', 'to_transaction'),
            'classes': ('collapse',)
        }),
        ('Processing', {
            'fields': ('processed_by', 'processed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


