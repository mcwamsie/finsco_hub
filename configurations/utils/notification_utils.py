"""
Notification utilities for Django views to work with Notyf frontend notifications.
"""
import json
from django.http import HttpResponse
from django.contrib import messages


class NotificationMixin:
    """
    Mixin to add notification functionality to Django views.
    """
    
    def add_notification(self, request, message, notification_type='success'):
        """
        Add a notification that will be displayed using Notyf.
        
        Args:
            request: Django request object
            message: Notification message
            notification_type: Type of notification ('success', 'error', 'warning', 'info')
        """
        # Map notification types to Django message tags
        tag_mapping = {
            'success': messages.SUCCESS,
            'error': messages.ERROR,
            'warning': messages.WARNING,
            'info': messages.INFO,
        }
        
        tag = tag_mapping.get(notification_type, messages.SUCCESS)
        messages.add_message(request, tag, message)
    
    def success_notification(self, request, message):
        """Add a success notification."""
        self.add_notification(request, message, 'success')
    
    def error_notification(self, request, message):
        """Add an error notification."""
        self.add_notification(request, message, 'error')
    
    def warning_notification(self, request, message):
        """Add a warning notification."""
        self.add_notification(request, message, 'warning')
    
    def info_notification(self, request, message):
        """Add an info notification."""
        self.add_notification(request, message, 'info')


def htmx_notification_response(message, notification_type='success', content='', status=200):
    """
    Create an HTMX response with notification trigger.
    
    Args:
        message: Notification message
        notification_type: Type of notification ('success', 'error', 'warning', 'info')
        content: Response content (optional)
        status: HTTP status code
    
    Returns:
        HttpResponse with HX-Trigger header for notifications
    """
    response = HttpResponse(content, status=status)
    
    trigger_data = {
        'notification': {
            'type': notification_type,
            'message': message
        }
    }
    
    response['HX-Trigger'] = json.dumps(trigger_data)
    return response


def htmx_success_response(message, content=''):
    """Create an HTMX success notification response."""
    return htmx_notification_response(message, 'success', content)


def htmx_error_response(message, content='', status=200):
    """Create an HTMX error notification response."""
    return htmx_notification_response(message, 'error', content, status)


def htmx_warning_response(message, content=''):
    """Create an HTMX warning notification response."""
    return htmx_notification_response(message, 'warning', content)


def htmx_info_response(message, content=''):
    """Create an HTMX info notification response."""
    return htmx_notification_response(message, 'info', content)


# Decorator for adding notifications to function-based views
def with_notifications(view_func):
    """
    Decorator to add notification methods to function-based views.
    
    Usage:
        @with_notifications
        def my_view(request):
            request.success_notification("Operation successful!")
            return render(request, 'template.html')
    """
    def wrapper(request, *args, **kwargs):
        # Add notification methods to request object
        request.success_notification = lambda msg: messages.success(request, msg)
        request.error_notification = lambda msg: messages.error(request, msg)
        request.warning_notification = lambda msg: messages.warning(request, msg)
        request.info_notification = lambda msg: messages.info(request, msg)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper