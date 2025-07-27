from django.core.management.base import BaseCommand

from configurations.utils.sms_service import SMSService


class Command(BaseCommand):
    help = 'Test SMS gateway connectivity'

    def add_arguments(self, parser):
        parser.add_argument('--phone', required=True, help='Phone number to test')
        parser.add_argument('--message', default='Test message from Medical Aid System')

    def handle(self, *args, **options):
        try:
            sms_service = SMSService()

            result = sms_service.send_sms(
                recipient=options['phone'],
                message=options['message'],
                message_type='notification'
            )

            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f"SMS sent successfully! Message ID: {result['message_id']}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"SMS failed: {result['error']}")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Test failed: {str(e)}")
            )