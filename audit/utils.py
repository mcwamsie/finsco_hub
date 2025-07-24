from django.core.exceptions import FieldDoesNotExist
from django.db import models
import json


def get_client_ip(request):
    """Extract client IP address from request"""
    if not request:
        return None
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extract user agent from request"""
    if not request:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')


def get_model_changes(original, current):
    """
    Compare two model instances and return a dictionary of changes
    """
    changes = {}
    
    # Get all fields from the model
    for field in current._meta.fields:
        field_name = field.name
        
        try:
            old_value = getattr(original, field_name)
            new_value = getattr(current, field_name)
            
            # Skip if values are the same
            if old_value == new_value:
                continue
            
            # Handle different field types
            if isinstance(field, models.DateTimeField):
                old_value = old_value.isoformat() if old_value else None
                new_value = new_value.isoformat() if new_value else None
            elif isinstance(field, models.DateField):
                old_value = old_value.isoformat() if old_value else None
                new_value = new_value.isoformat() if new_value else None
            elif isinstance(field, models.TimeField):
                old_value = old_value.isoformat() if old_value else None
                new_value = new_value.isoformat() if new_value else None
            elif isinstance(field, models.ForeignKey):
                old_value = str(old_value) if old_value else None
                new_value = str(new_value) if new_value else None
            elif isinstance(field, models.FileField):
                old_value = old_value.name if old_value else None
                new_value = new_value.name if new_value else None
            elif isinstance(field, models.JSONField):
                old_value = json.dumps(old_value) if old_value else None
                new_value = json.dumps(new_value) if new_value else None
            else:
                old_value = str(old_value) if old_value is not None else None
                new_value = str(new_value) if new_value is not None else None
            
            # Store the change
            changes[field_name] = {
                'old': old_value,
                'new': new_value
            }
            
        except (AttributeError, FieldDoesNotExist):
            continue
    
    return changes


def log_data_export(user, export_type, file_format, record_count, file_size, filters=None, request=None):
    """
    Utility function to log data exports
    """
    from .models import DataExport
    
    DataExport.objects.create(
        user=user,
        export_type=export_type,
        file_format=file_format,
        record_count=record_count,
        file_size=file_size,
        filters_applied=filters or {},
        ip_address=get_client_ip(request) if request else None,
    )


def log_system_event(event_type, title, description, user=None, request=None, **kwargs):
    """
    Utility function to log system events
    """
    from .models import SystemEvent
    
    SystemEvent.objects.create(
        event_type=event_type,
        title=title,
        description=description,
        user=user,
        ip_address=get_client_ip(request) if request else None,
        module=kwargs.get('module', ''),
        function_name=kwargs.get('function_name', ''),
        line_number=kwargs.get('line_number'),
        error_code=kwargs.get('error_code', ''),
        stack_trace=kwargs.get('stack_trace', ''),
    )


def log_audit_event(user, action, content_object, changes=None, reason='', request=None):
    """
    Utility function to manually log audit events
    """
    from .models import AuditLog
    from django.contrib.contenttypes.models import ContentType
    
    AuditLog.objects.create(
        user=user,
        action=action,
        content_type=ContentType.objects.get_for_model(content_object),
        object_id=content_object.pk,
        object_repr=str(content_object)[:200],
        changes=changes or {},
        reason=reason,
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else '',
        session_key=request.session.session_key if request and hasattr(request, 'session') else '',
        module=content_object._meta.app_label,
    )


class AuditMixin:
    """
    Mixin to add audit functionality to views
    """
    def log_view_access(self, request, obj=None):
        """Log when a view is accessed"""
        if obj:
            log_audit_event(
                user=request.user if request.user.is_authenticated else None,
                action='VIEW',
                content_object=obj,
                request=request
            )


def get_audit_summary(user=None, days=30):
    """
    Get audit summary for a user or system-wide
    """
    from .models import AuditLog, LoginAttempt, SystemEvent
    from django.utils import timezone
    from datetime import timedelta
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Base querysets
    audit_qs = AuditLog.objects.filter(timestamp__gte=start_date)
    login_qs = LoginAttempt.objects.filter(timestamp__gte=start_date)
    event_qs = SystemEvent.objects.filter(timestamp__gte=start_date)
    
    if user:
        audit_qs = audit_qs.filter(user=user)
        login_qs = login_qs.filter(username=user.username)
        event_qs = event_qs.filter(user=user)
    
    return {
        'total_actions': audit_qs.count(),
        'creates': audit_qs.filter(action='CREATE').count(),
        'updates': audit_qs.filter(action='UPDATE').count(),
        'deletes': audit_qs.filter(action='DELETE').count(),
        'views': audit_qs.filter(action='VIEW').count(),
        'logins': login_qs.filter(status='SUCCESS').count(),
        'failed_logins': login_qs.filter(status='FAILED').count(),
        'system_errors': event_qs.filter(event_type='ERROR').count(),
        'unresolved_events': event_qs.filter(resolved=False).count(),
    }