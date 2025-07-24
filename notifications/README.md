# Notification Service

A comprehensive notification system for the Fisco Hub application that integrates with the User model's extensive notification preferences.

## Features

- **Multi-channel delivery**: Email, SMS, Push notifications, and In-app notifications
- **User preference integration**: Leverages the User model's detailed notification preferences
- **Quiet hours support**: Respects user-defined quiet hours for SMS and email
- **Notification categories**: Organized by member, claims, account, provider, security, etc.
- **Delivery tracking**: Tracks delivery status and errors for each channel
- **Bulk notifications**: Send notifications to multiple users efficiently
- **API endpoints**: RESTful API for notification management
- **Management commands**: CLI tools for sending notifications
- **Comprehensive logging**: Detailed logging of all notification activities

## Models

### NotificationType
Defines different types of notifications with default channel settings.

```python
# Example notification types
GENERAL = "General notifications"
SECURITY = "Security alerts"
SYSTEM = "System notifications"
MARKETING = "Marketing messages"
```

### Notification
Individual notification instances with delivery status tracking. Links to the User model for recipient information.

```python
# Key fields:
- user: ForeignKey to User model
- notification_type: ForeignKey to NotificationType
- title: Notification title
- message: Notification content
- is_read: Boolean read status
- email_sent: Boolean email delivery status
- sms_sent: Boolean SMS delivery status
- created_at: Timestamp
```

### NotificationLog
Tracks detailed delivery information for each notification channel.

```python
# Key fields:
- notification: ForeignKey to Notification
- channel: Delivery channel (email, sms, push, in_app)
- status: Delivery status (pending, sent, delivered, failed)
- sent_at: Delivery timestamp
- error_message: Error details if delivery failed
```

## User Model Integration

The notification system leverages the User model's extensive notification preferences:

### Global Notification Settings
- `receive_email_notifications`: Master email toggle
- `receive_sms_notifications`: Master SMS toggle
- `phone_number`: SMS delivery number

### Quiet Hours
- `sms_quiet_hours_enabled`: SMS quiet hours toggle
- `sms_quiet_hours_start`: SMS quiet hours start time
- `sms_quiet_hours_end`: SMS quiet hours end time
- `email_quiet_hours_enabled`: Email quiet hours toggle
- `email_quiet_hours_start`: Email quiet hours start time
- `email_quiet_hours_end`: Email quiet hours end time

### Specific Notification Preferences
The User model includes detailed preferences for each notification type:
- `notify_member_registration`: Member registration notifications
- `notify_member_registration_sms`: SMS for member registration
- `notify_member_registration_email`: Email for member registration
- And many more specific notification fields...

## Services

### NotificationService
Main service class for notification operations:

```python
from notifications.services import NotificationService

# Send single notification
notification = NotificationService.send_notification(
    user=user,
    notification_type='SECURITY',
    title='Security Alert',
    message='Suspicious login detected'
)

# Send bulk notifications
notifications = NotificationService.send_bulk_notifications(
    users=[user1, user2, user3],
    notification_type='GENERAL',
    title='System Maintenance',
    message='Scheduled maintenance tonight'
)

# Get unread count
count = NotificationService.get_unread_count(user)

# Mark as read
NotificationService.mark_as_read(notification_id, user)

# Mark all as read
count = NotificationService.mark_all_as_read(user)

# Get recent notifications
notifications = NotificationService.get_recent_notifications(user, limit=10)
```

## User Model Helper Methods

The User model includes several notification-related methods:

```python
# Get notification statistics
stats = user.get_notification_statistics(days=30)

# Get notification field choices for admin
choices = User.get_notification_field_choices()

# Get user notification preferences for a specific activity
prefs = get_user_notification_preferences(user, 'member_registration')

# Send enhanced notification (used in signals)
send_enhanced_notification(
    user=user,
    activity='member_registration',
    title='Welcome!',
    message='Registration successful',
    context={'username': user.username}
)
```

## API Endpoints

### Authentication Required Endpoints

- `GET /notifications/api/list/` - List user's notifications
- `GET /notifications/api/unread-count/` - Get unread notification count
- `GET /notifications/api/recent/` - Get recent notifications
- `POST /notifications/api/<id>/read/` - Mark notification as read
- `POST /notifications/api/mark-all-read/` - Mark all notifications as read
- `GET /notifications/api/types/` - Get available notification types

### Admin Only Endpoints

- `POST /notifications/api/create/` - Create new notification

### Example API Usage

```javascript
// Get unread count
fetch('/notifications/api/unread-count/')
  .then(response => response.json())
  .then(data => console.log('Unread:', data.unread_count));

// Mark notification as read
fetch('/notifications/api/123/read/', {
  method: 'POST',
  headers: {
    'X-CSRFToken': getCookie('csrftoken'),
    'Content-Type': 'application/json'
  }
});

// Create bulk notification (admin only)
fetch('/notifications/api/create/', {
  method: 'POST',
  headers: {
    'X-CSRFToken': getCookie('csrftoken'),
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_ids: [1, 2, 3],
    notification_type: 'GENERAL',
    title: 'System Update',
    message: 'System will be updated tonight'
  })
});
```

## Management Commands

### Send Notification Command

```bash
# Send to specific user
python manage.py send_notification --title "Test" --message "Hello" --user username

# Send to all active users
python manage.py send_notification --title "Announcement" --message "Important update" --all-users

# Send to staff only
python manage.py send_notification --title "Staff Notice" --message "Meeting tomorrow" --staff-only

# Specify notification type
python manage.py send_notification --title "Security Alert" --message "Password changed" --type SECURITY --user username
```

## Signals

The notification system includes signal handlers for automatic notification creation:

```python
from notifications.signals import create_notification

# Create notification programmatically
create_notification(
    recipient=user,
    notification_type_name='GENERAL',
    title='Welcome!',
    message='Thanks for joining our platform'
)
```

## Configuration

### Settings

Add to your Django settings:

```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'notifications.apps.NotificationsConfig',
]

# Optional: Configure notification settings
NOTIFICATION_SETTINGS = {
    'DEFAULT_FROM_EMAIL': 'noreply@yoursite.com',
    'CLEANUP_DAYS': 30,  # Days to keep old notifications
    'MAX_NOTIFICATIONS_PER_USER': 1000,
}
```

### URL Configuration

```python
# urls.py
urlpatterns = [
    # ... other patterns
    path('notifications/', include('notifications.urls')),
]
```

## Templates

The notification system includes basic templates that you can customize:

- `notifications/notification_list.html` - Notification list page
- `notifications/notification_detail.html` - Notification detail page
- `notifications/preferences.html` - User preferences page
- `notifications/create_notification.html` - Admin notification creation page

## Usage Examples

### Basic Notification Creation

```python
from notifications.services import NotificationService

# Simple notification
NotificationService.send_notification(
    user=request.user,
    notification_type='GENERAL',
    title='Profile Updated',
    message='Your profile has been successfully updated.'
)
```

### Bulk Notifications

```python
from django.contrib.auth import get_user_model
from notifications.services import NotificationService

User = get_user_model()

# Notify all active users
active_users = User.objects.filter(is_active=True)
NotificationService.send_bulk_notifications(
    users=list(active_users),
    notification_type='SYSTEM',
    title='Maintenance Notice',
    message='System maintenance scheduled for tonight at 2 AM.'
)
```

### Custom Notification Types

```python
from notifications.models import NotificationType

# Create custom notification type
custom_type = NotificationType.objects.create(
    name='CUSTOM_ALERT',
    description='Custom alert notifications',
    is_active=True
)
```

### User Preference Management

User preferences are managed through the User model fields:

```python
from django.contrib.auth import get_user_model

User = get_user_model()

# Update user notification preferences
user = User.objects.get(username='john')
user.receive_email_notifications = True
user.receive_sms_notifications = False
user.sms_quiet_hours_enabled = True
user.sms_quiet_hours_start = '22:00'
user.sms_quiet_hours_end = '08:00'
user.notify_member_registration = True
user.notify_member_registration_email = True
user.notify_member_registration_sms = False
user.save()

# Get user notification preferences for a specific activity
from authentication.models import get_user_notification_preferences

prefs = get_user_notification_preferences(user, 'member_registration')
print(f"Can receive notifications: {prefs['can_receive']}")
print(f"Active channels: {prefs['active_channels']}")
```

## Best Practices

1. **Use Appropriate Notification Types**: Choose the right notification type for your message
2. **Respect User Preferences**: Always check user preferences before sending notifications
3. **Batch Operations**: Use bulk operations for sending multiple notifications
4. **Cleanup Regularly**: Use the cleanup utility to remove old notifications
5. **Monitor Performance**: Keep track of notification statistics and delivery rates
6. **Test Thoroughly**: Test notification delivery across all channels
7. **Handle Errors Gracefully**: Implement proper error handling for failed deliveries

## Troubleshooting

### Common Issues

1. **Notifications not sending**: Check user preferences in the User model
2. **Email delivery issues**: Verify email configuration in Django settings
3. **Performance problems**: Consider using Celery for asynchronous notification processing
4. **Database growth**: Implement regular cleanup of old notifications

### Debug Mode

Enable debug logging for notifications:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'notifications.log',
        },
    },
    'loggers': {
        'notifications': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## Contributing

When contributing to the notification system:

1. Follow Django best practices
2. Add tests for new functionality
3. Update documentation
4. Consider backward compatibility
5. Test across different notification channels

## License

This notification system is part of the larger Django project and follows the same licensing terms.