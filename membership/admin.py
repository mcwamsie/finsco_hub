from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateWidget

from configurations.models import Member, Package
from membership.models import Beneficiary, TopUp


class BeneficiaryResource(resources.ModelResource):
    member = fields.Field(
        column_name='member_number',
        attribute='member',
        widget=ForeignKeyWidget(Member, 'membership_number')
    )
    package = fields.Field(
        column_name='package',
        attribute='package',
        widget=ForeignKeyWidget(Package, 'name')
    )
    principal = fields.Field(
        column_name='principal_membership_dependent',
        attribute='principal',
        widget=ForeignKeyWidget(Beneficiary, 'membership_number')
    )
    date_of_birth = fields.Field(
        column_name='date_of_birth',
        attribute='date_of_birth',
        widget=DateWidget(format='%Y-%m-%d')
    )

    class Meta:
        model = Beneficiary
        import_id_fields = ('membership_number', 'dependent_code')
        fields = ('membership_number', 'dependent_code', 'first_name', 'last_name',
                  'middle_name', 'national_id_number', 'date_of_birth', 'gender',
                  'mobile', 'email', 'physical_address', 'member_number', 'relationship',
                  'status', 'type', 'package', 'annual_limit', 'benefit_start_date',
                  'principal_membership_dependent')
        export_order = ('membership_number', 'dependent_code', 'first_name', 'last_name',
                        'national_id_number', 'type', 'status', 'annual_limit')

    def before_import_row(self, row, **kwargs):
        # Validate gender choices
        if row.get('gender') and row['gender'] not in ['M', 'F', 'O']:
            raise ValueError(f"Invalid gender: {row['gender']}")

        # Validate beneficiary type
        if row.get('type') and row['type'] not in ['P', 'S', 'D', 'E']:
            raise ValueError(f"Invalid beneficiary type: {row['type']}")


@admin.register(Beneficiary)
class BeneficiaryAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = BeneficiaryResource
    list_display = ('membership_number', 'dependent_code', 'first_name', 'last_name',
                    'type', 'status', 'annual_limit')
    list_filter = ('type', 'status', 'gender', 'package')
    search_fields = ('membership_number', 'dependent_code', 'first_name', 'last_name',
                     'national_id_number')
    readonly_fields = ('membership_number', 'dependent_code')

class TopUpResource(resources.ModelResource):
    member = fields.Field(
        column_name='member_number',
        attribute='member',
        widget=ForeignKeyWidget(Member, 'membership_number')
    )
    payment_method = fields.Field(
        column_name='payment_method',
        attribute='payment_method',
        widget=ForeignKeyWidget('configurations.PaymentMethod', 'name')
    )

    class Meta:
        model = TopUp
        import_id_fields = ('top_up_number',)
        fields = ('top_up_number', 'member_number', 'amount', 'admin_fee', 'net_amount',
                 'payment_method', 'status', 'mobile_number', 'bank_reference')
        export_order = ('top_up_number', 'member_number', 'amount', 'status', 'request_date')

@admin.register(TopUp)
class TopUpAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_class = TopUpResource
    list_display = ('top_up_number', 'member', 'amount', 'status', 'request_date')
    list_filter = ('status', 'payment_method', 'request_date')
    search_fields = ('top_up_number', 'member__membership_number', 'member__name')
    readonly_fields = ('top_up_number',)
    date_hierarchy = 'request_date'

