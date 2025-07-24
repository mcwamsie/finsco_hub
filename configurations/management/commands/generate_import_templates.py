import os

from django.core.management.base import BaseCommand
from django.http import HttpResponse
import csv
import io


class Command(BaseCommand):
    help = 'Generate CSV templates for data import'

    def add_arguments(self, parser):
        parser.add_argument(
            '--template',
            choices=['currency', 'tier', 'package', 'member', 'beneficiary',
                     'service_provider', 'service', 'agent', 'all'],
            default='all',
            help='Template type to generate'
        )
        parser.add_argument(
            '--output-dir',
            default='./import_templates/',
            help='Output directory for templates'
        )

    def handle(self, *args, **options):
        import os
        output_dir = options['output_dir']
        os.makedirs(output_dir, exist_ok=True)

        templates = {
            'currency': self.generate_currency_template,
            'tier': self.generate_tier_template,
            'package': self.generate_package_template,
            'member': self.generate_member_template,
            'beneficiary': self.generate_beneficiary_template,
            'service_provider': self.generate_service_provider_template,
            'service': self.generate_service_template,
            'agent': self.generate_agent_template,
        }

        if options['template'] == 'all':
            for template_name, generator in templates.items():
                self.generate_template(template_name, generator, output_dir)
        else:
            template_name = options['template']
            if template_name in templates:
                self.generate_template(template_name, templates[template_name], output_dir)

        self.stdout.write(
            self.style.SUCCESS(f'Templates generated in {output_dir}')
        )

    def generate_template(self, name, generator, output_dir):
        filename = os.path.join(output_dir, f'{name}_import_template.csv')
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            generator(csvfile)
        self.stdout.write(f'Generated: {filename}')

    def generate_currency_template(self, csvfile):
        writer = csv.writer(csvfile)
        writer.writerow(['code', 'name', 'symbol', 'exchange_rate', 'is_base_currency', 'is_active'])
        writer.writerow(['USD', 'US Dollar', ' ', '1.00', 'True', 'True'])
        writer.writerow(['ZWL', 'Zimbabwe Dollar', 'Z ', '350.00', 'False', 'True'])
        writer.writerow(['ZAR', 'South African Rand', 'R', '18.50', 'False', 'True'])

    def generate_tier_template(self, csvfile):
        writer = csv.writer(csvfile)
        writer.writerow(['level', 'name', 'description', 'requirements', 'is_active'])
        writer.writerow(['1', 'Tier 1', 'Basic service providers', 'Basic registration', 'True'])
        writer.writerow(['2', 'Tier 2', 'Intermediate service providers', 'Additional qualifications', 'True'])
        writer.writerow(['3', 'Tier 3', 'Premium service providers', 'Advanced certifications', 'True'])

    def generate_package_template(self, csvfile):
        writer = csv.writer(csvfile)
        writer.writerow(['name', 'description', 'global_annual_limit', 'global_family_limit',
                         'monthly_contribution', 'child_monthly_contribution', 'is_active'])
        writer.writerow(['Basic Plan', 'Basic healthcare coverage', '5000.00', '15000.00',
                         '50.00', '25.00', 'True'])
        writer.writerow(['Premium Plan', 'Comprehensive healthcare coverage', '15000.00', '45000.00',
                         '150.00', '75.00', 'True'])

    def generate_member_template(self, csvfile):
        writer = csv.writer(csvfile)
        writer.writerow(['membership_number', 'name', 'type', 'alias', 'currency', 'address_line_1',
                         'address_line_2', 'mobile', 'telephone', 'email', 'signing_rule', 'status',
                         'sponsor', 'stop_order_form', 'stop_order_amount', 'global_annual_limit',
                         'parent_membership_number', 'default_package', 'registered_by_agent'])
        writer.writerow(['10000001', 'ABC Corporation', 'CO', 'ABC Corp', 'USD', '123 Main Street',
                         'Suite 100', '+263712345678', '+263242123456', 'info@abc.com', 'D', 'A',
                         'E', 'per_month', '1000.00', '50000.00', '', 'Premium Plan', 'AG2401001'])
        writer.writerow(['40000001', 'John Doe', 'IN', 'Johnny', 'USD', '456 Oak Avenue',
                         '', '+263712345679', '', 'john@email.com', 'S', 'A', 'S', 'off', '0.00',
                         '10000.00', '', 'Basic Plan', 'AG2401001'])

    def generate_beneficiary_template(self, csvfile):
        writer = csv.writer(csvfile)
        writer.writerow(['membership_number', 'dependent_code', 'first_name', 'last_name', 'middle_name',
                         'national_id_number', 'date_of_birth', 'gender', 'mobile', 'email',
                         'physical_address', 'member_number', 'relationship', 'status', 'type',
                         'package', 'annual_limit', 'benefit_start_date'])
        writer.writerow(['10000001', '000', 'John', 'Smith', 'Michael', '12-345678-A-12',
                         '1985-06-15', 'M', '+263712345678', 'john@company.com', '123 Main St',
                         '10000001', 'Principal', 'A', 'P', 'Premium Plan', '15000.00', '2024-01-01'])
        writer.writerow(['10000001', '001', 'Jane', 'Smith', 'Mary', '12-345679-B-12',
                         '1987-08-20', 'F', '+263712345679', 'jane@company.com', '123 Main St',
                         '10000001', 'Spouse', 'A', 'S', 'Premium Plan', '15000.00', '2024-01-01'])

    def generate_service_provider_template(self, csvfile):
        writer = csv.writer(csvfile)
        writer.writerow(['account_no', 'identification_no', 'name', 'alias', 'address_line_1',
                         'address_line_2', 'mobile', 'telephone', 'email', 'tier', 'type',
                         'category', 'signing_rule', 'status', 'bp_number', 'region',
                         'council_number', 'hpa_number', 'is_from_network', 'is_third_party'])
        writer.writerow(['202401001', 'AFHOZ001', 'City Medical Center', 'CMC', '789 Health St',
                         'Medical District', '+263712345680', '+263242123457', 'info@cmc.co.zw',
                         'Tier 1', 'Hospital', 'General Practice', 'D', 'A', 'TIN123456',
                         'Harare', 'MED001', 'HPA001', 'True', 'False'])

    def generate_service_template(self, csvfile):
        writer = csv.writer(csvfile)
        writer.writerow(['code', 'description', 'category', 'unit_of_measure', 'base_price',
                         'is_active', 'requires_authorization', 'requires_referral', 'is_emergency_service'])
        writer.writerow(['GP001', 'General Practice Consultation', 'General Practice', 'Each',
                         '50.00', 'True', 'False', 'False', 'False'])
        writer.writerow(['LAB001', 'Full Blood Count', 'Laboratory', 'Each', '25.00',
                         'True', 'False', 'False', 'False'])
        writer.writerow(['XRAY001', 'Chest X-Ray', 'Radiology', 'Each', '75.00',
                         'True', 'True', 'True', 'False'])

    def generate_agent_template(self, csvfile):
        writer = csv.writer(csvfile)
        writer.writerow(['account_no', 'name', 'alias', 'identification_no', 'address_line_1',
                         'mobile', 'telephone', 'email', 'type', 'base_commission_rate',
                         'status', 'region', 'currency'])
        writer.writerow(['AG2401001', 'Sales Agent One', 'Agent1', '12-123456-C-12',
                         '321 Agent Street', '+263712345681', '', 'agent1@company.com',
                         'I', '2.50', 'A', 'Harare', 'USD'])

