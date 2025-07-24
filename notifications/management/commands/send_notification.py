from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from notifications.services import NotificationService

User = get_user_model()


class Command(BaseCommand):
    help = 'Send notifications to users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--title',
            type=str,
            required=True,
            help='Notification title'
        )
        parser.add_argument(
            '--message',
            type=str,
            required=True,
            help='Notification message'
        )
        parser.add_argument(
            '--type',
            type=str,
            default='GENERAL',
            help='Notification type (default: GENERAL)'
        )
        parser.add_argument(
            '--users',
            type=str,
            nargs='*',
            help='Specific usernames to notify (space-separated)'
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Send to all active users'
        )
        parser.add_argument(
            '--staff-only',
            action='store_true',
            help='Send to staff users only'
        )
        parser.add_argument(
            '--superuser-only',
            action='store_true',
            help='Send to superusers only'
        )

    def handle(self, *args, **options):
        title = options['title']
        message = options['message']
        notification_type = options['type']
        
        # Determine target users
        if options['all_users']:
            users = User.objects.filter(is_active=True)
            target_desc = "all active users"
        elif options['staff_only']:
            users = User.objects.filter(is_active=True, is_staff=True)
            target_desc = "all staff users"
        elif options['superuser_only']:
            users = User.objects.filter(is_active=True, is_superuser=True)
            target_desc = "all superusers"
        elif options['users']:
            usernames = options['users']
            users = User.objects.filter(username__in=usernames, is_active=True)
            missing_users = set(usernames) - set(users.values_list('username', flat=True))
            if missing_users:
                self.stdout.write(
                    self.style.WARNING(f"Users not found or inactive: {', '.join(missing_users)}")
                )
            target_desc = f"users: {', '.join(users.values_list('username', flat=True))}"
        else:
            raise CommandError("You must specify target users using --users, --all-users, --staff-only, or --superuser-only")

        if not users.exists():
            raise CommandError("No users found matching the criteria")

        # Confirm before sending
        user_count = users.count()
        self.stdout.write(f"About to send notification to {user_count} users ({target_desc})")
        self.stdout.write(f"Title: {title}")
        self.stdout.write(f"Message: {message}")
        self.stdout.write(f"Type: {notification_type}")
        
        if not options.get('verbosity', 1) >= 2:  # Skip confirmation in verbose mode
            confirm = input("Continue? (y/N): ")
            if confirm.lower() != 'y':
                self.stdout.write("Cancelled.")
                return

        # Send notifications
        try:
            notifications = NotificationService.send_bulk_notifications(
                users=list(users),
                notification_type=notification_type,
                title=title,
                message=message
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully sent {len(notifications)} notifications to {user_count} users"
                )
            )
            
        except Exception as e:
            raise CommandError(f"Error sending notifications: {str(e)}")