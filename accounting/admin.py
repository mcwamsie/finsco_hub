from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from accounting.models import MemberAccount
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


