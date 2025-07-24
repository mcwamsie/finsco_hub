from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import connection
from .models import AuditLog, LoginAttempt
from .utils import get_client_ip, get_user_agent, get_model_changes
import threading

# Thread-local storage for request data
_thread_locals = threading.local()


import sys

def is_migration_running():
    """Check if we're currently running migrations"""
    # Check if we're running a Django management command
    if 'manage.py' in sys.argv[0] or 'django-admin' in sys.argv[0]:
        # Check if the command is migrate, makemigrations, or similar
        if len(sys.argv) > 1 and sys.argv[1] in ['migrate', 'makemigrations', 'sqlmigrate', 'showmigrations']:
            return True
    
    # Also check if ContentType table is accessible
    try:
        ContentType.objects.exists()
        return False
    except Exception:
        return True


def set_current_request(request):
    """Store the current request in thread-local storage"""
    _thread_locals.request = request


def get_current_request():
    """Get the current request from thread-local storage"""
    return getattr(_thread_locals, 'request', None)


@receiver(pre_save)
def capture_model_changes(sender, instance, **kwargs):
    """Capture changes before saving a model instance"""
    # Skip audit models to prevent infinite loops
    if sender._meta.app_label == 'audit':
        return
    
    # Skip if this is a new instance
    if instance.pk is None:
        return
    
    try:
        # Get the original instance from database
        original = sender.objects.get(pk=instance.pk)
        changes = get_model_changes(original, instance)
        
        # Store changes in thread-local storage
        if not hasattr(_thread_locals, 'model_changes'):
            _thread_locals.model_changes = {}
        
        _thread_locals.model_changes[f"{sender._meta.label}_{instance.pk}"] = changes
    except sender.DoesNotExist:
        pass


@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """Log model save operations"""
    # Skip if we're running migrations
    if is_migration_running():
        return
    
    # Skip audit models to prevent infinite loops
    if sender._meta.app_label == 'audit':
        return
    
    # Skip User model saves during login to prevent noise
    if sender._meta.model_name == 'user' and hasattr(instance, 'last_login'):
        return
    
    request = get_current_request()
    user = getattr(request, 'user', None) if request else None
    
    # Determine action
    action = 'CREATE' if created else 'UPDATE'
    
    # Get changes for updates
    changes = {}
    if not created:
        model_key = f"{sender._meta.label}_{instance.pk}"
        changes = getattr(_thread_locals, 'model_changes', {}).get(model_key, {})
    
    # Create audit log entry
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        content_type=ContentType.objects.get_for_model(sender),
        object_id=str(instance.pk) if instance.pk is not None else None,
        object_repr=str(instance)[:200],
        changes=changes,
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else '',
        session_key=request.session.session_key if request and hasattr(request, 'session') else '',
        module=sender._meta.app_label,
    )


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """Log model delete operations"""
    # Skip if we're running migrations
    if is_migration_running():
        return
    
    # Skip audit models to prevent infinite loops
    if sender._meta.app_label == 'audit':
        return
    
    request = get_current_request()
    user = getattr(request, 'user', None) if request else None
    
    # Create audit log entry
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action='DELETE',
        content_type=ContentType.objects.get_for_model(sender),
        object_id=str(instance.pk) if instance.pk is not None else None,
        object_repr=str(instance)[:200],
        changes={'deleted_object': str(instance)},
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else '',
        session_key=request.session.session_key if request and hasattr(request, 'session') else '',
        module=sender._meta.app_label,
    )


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user login"""
    # Skip if we're running migrations
    if is_migration_running():
        return
    
    # Create audit log
    AuditLog.objects.create(
        user=user,
        action='LOGIN',
        content_type=ContentType.objects.get_for_model(user),
        object_id=user.pk,
        object_repr=str(user)[:200],
        changes={'login_time': timezone.now().isoformat()},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        session_key=request.session.session_key,
        module='authentication',
    )
    
    # Create login attempt record
    LoginAttempt.objects.create(
        username=user.username,
        status='SUCCESS',
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout"""
    # Skip if we're running migrations
    if is_migration_running():
        return
    
    if user:  # user might be None if session expired
        AuditLog.objects.create(
            user=user,
            action='LOGOUT',
            content_type=ContentType.objects.get_for_model(user),
            object_id=user.pk,
            object_repr=str(user)[:200],
            changes={'logout_time': timezone.now().isoformat()},
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key if hasattr(request, 'session') else '',
            module='authentication',
        )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """Log failed login attempts"""
    # Skip if we're running migrations
    if is_migration_running():
        return
    
    username = credentials.get('username', 'unknown')
    
    # Create login attempt record
    LoginAttempt.objects.create(
        username=username,
        status='FAILED',
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    # Create audit log
    AuditLog.objects.create(
        user=None,
        action='LOGIN_FAILED',
        content_type=None,
        object_id=None,
        object_repr=f"Failed login for username: {username}",
        changes={'username': username, 'failure_time': timezone.now().isoformat()},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        session_key=request.session.session_key if hasattr(request, 'session') else '',
        module='authentication',
    )