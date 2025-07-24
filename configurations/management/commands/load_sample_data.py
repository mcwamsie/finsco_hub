from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Load sample data for testing import functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            choices=['currency', 'tier', 'agent', 'all'],
            default='all',
            help='Model to load sample data for'
        )

    def handle(self, *args, **options):
        if options['model'] in ['currency', 'all']:
            self.load_currencies()

        if options['model'] in ['tier', 'all']:
            self.load_tiers()

        if options['model'] in ['agent', 'all']:
            self.load_agents()

        self.stdout.write(self.style.SUCCESS('Sample data loaded successfully'))

    def load_currencies(self):
        from configurations.models import Currency

        currencies = [
            {'code': 'USD', 'name': 'US Dollar', 'symbol': ' ', 'exchange_rate': 1.00, 'is_base_currency': True},
            {'code': 'ZWL', 'name': 'Zimbabwe Dollar', 'symbol': 'Z ', 'exchange_rate': 350.00},
            {'code': 'ZAR', 'name': 'South African Rand', 'symbol': 'R', 'exchange_rate': 18.50},
            {'code': 'BWP', 'name': 'Botswana Pula', 'symbol': 'P', 'exchange_rate': 13.50},
        ]

        for currency_data in currencies:
            currency, created = Currency.objects.get_or_create(
                code=currency_data['code'],
                defaults=currency_data
            )
            if created:
                self.stdout.write(f'Created currency: {currency.code}')

    def load_tiers(self):
        from configurations.models import Tier

        tiers = [
            {'level': 1, 'name': 'Tier 1', 'description': 'Basic service providers'},
            {'level': 2, 'name': 'Tier 2', 'description': 'Intermediate service providers'},
            {'level': 3, 'name': 'Tier 3', 'description': 'Premium service providers'},
        ]

        for tier_data in tiers:
            tier, created = Tier.objects.get_or_create(
                level=tier_data['level'],
                defaults=tier_data
            )
            if created:
                self.stdout.write(f'Created tier: {tier.name}')

    def load_agents(self):
        from configurations.models import Agent, Currency

        try:
            currency = Currency.objects.get(code='USD')
        except Currency.DoesNotExist:
            self.stdout.write(self.style.ERROR('USD currency not found. Load currencies first.'))
            return

        agents = [
            {
                'name': 'Sample Agent One',
                'alias': 'Agent1',
                'identification_no': '12-123456-A-12',
                'address_line_1': '123 Agent Street',
                'mobile': '+263712345678',
                'email': 'agent1@company.com',
                'type': 'I',
                'base_commission_rate': 2.50,
                'currency': currency,
            }
        ]

        for agent_data in agents:
            agent, created = Agent.objects.get_or_create(
                name=agent_data['name'],
                defaults=agent_data
            )
            if created:
                self.stdout.write(f'Created agent: {agent.name}')
