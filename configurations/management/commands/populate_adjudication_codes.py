from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Populate standard adjudication message codes'

    def handle(self, *args, **options):
        from services.models import AdjudicationMessageCode

        # Import the standard codes from the model
        from services.models import AdjudicationMessageCodeData

        created_count = 0

        for code, title, description, message_type in AdjudicationMessageCodeData.STANDARD_CODES:
            message_code, created = AdjudicationMessageCode.objects.get_or_create(
                code=code,
                defaults={
                    'title': title,
                    'description': description,
                    'message_type': message_type,
                    'category': code[:4],  # First 4 characters as category
                    'is_visible_to_provider': True,
                    'is_visible_to_member': message_type in ['APPROVAL', 'DECLINE'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f'Created message code: {code} - {title}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} message codes')
        )