from django.core.management.base import BaseCommand
from configurations.models import PaymentGateway
from configurations.utils.payment_service import PaymentGatewayService


class Command(BaseCommand):
    help = 'Refresh JWT tokens for payment gateways'

    def handle(self, *args, **options):
        jwt_gateways = PaymentGateway.objects.filter(
            auth_type='jwt',
            is_active=True
        )

        for gateway in jwt_gateways:
            try:
                service = PaymentGatewayService(gateway)
                token = service.get_valid_token()

                if token:
                    self.stdout.write(
                        self.style.SUCCESS(f"Token refreshed for {gateway.name}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to refresh token for {gateway.name}")
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error refreshing {gateway.name}: {str(e)}")
                )
