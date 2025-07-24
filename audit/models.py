from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import json

User = get_user_model()


class AuditLog(models.Model):
    """
    Custom audit log model to track all changes in the system
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
    ]

    # User who performed the action
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs'
    )
    
    # Action performed
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Object being audited (using generic foreign key)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional details
    object_repr = models.CharField(max_length=200, help_text="String representation of the object")
    
    # Changes made (JSON field to store before/after values)
    changes = models.JSONField(default=dict, blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    
    # Additional context
    reason = models.TextField(blank=True, help_text="Reason for the action")
    module = models.CharField(max_length=100, blank=True, help_text="Module/app where action occurred")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.user} {self.action} {self.object_repr} at {self.timestamp}"

    def get_changes_display(self):
        """Return a formatted display of changes"""
        if not self.changes:
            return "No changes recorded"
        
        changes_list = []
        for field, change in self.changes.items():
            if isinstance(change, dict) and 'old' in change and 'new' in change:
                changes_list.append(f"{field}: '{change['old']}' → '{change['new']}'")
            else:
                changes_list.append(f"{field}: {change}")
        
        return "; ".join(changes_list)


class LoginAttempt(models.Model):
    """
    Track login attempts for security monitoring
    """
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('BLOCKED', 'Blocked'),
    ]

    username = models.CharField(max_length=150)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    failure_reason = models.CharField(max_length=200, blank=True)
    
    # Geographic information (optional)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['username', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['status', 'timestamp']),
        ]
        verbose_name = 'Login Attempt'
        verbose_name_plural = 'Login Attempts'

    def __str__(self):
        return f"{self.username} - {self.status} at {self.timestamp}"


class DataExport(models.Model):
    """
    Track data exports for compliance and security
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='data_exports')
    export_type = models.CharField(max_length=100, help_text="Type of data exported")
    file_format = models.CharField(max_length=20, default='CSV')
    record_count = models.PositiveIntegerField(default=0)
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    
    # Filters applied during export
    filters_applied = models.JSONField(default=dict, blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # File information
    file_path = models.CharField(max_length=500, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Data Export'
        verbose_name_plural = 'Data Exports'

    def __str__(self):
        return f"{self.user} exported {self.export_type} at {self.timestamp}"


class SystemEvent(models.Model):
    """
    Track system-level events and errors
    """
    EVENT_TYPES = [
        ('ERROR', 'Error'),
        ('WARNING', 'Warning'),
        ('INFO', 'Information'),
        ('SECURITY', 'Security'),
        ('PERFORMANCE', 'Performance'),
        ('MAINTENANCE', 'Maintenance'),
    ]

    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Technical details
    module = models.CharField(max_length=100, blank=True)
    function_name = models.CharField(max_length=100, blank=True)
    line_number = models.PositiveIntegerField(null=True, blank=True)
    
    # Error details (if applicable)
    error_code = models.CharField(max_length=50, blank=True)
    stack_trace = models.TextField(blank=True)
    
    # Context
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(default=timezone.now)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='resolved_events'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['resolved', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
        verbose_name = 'System Event'
        verbose_name_plural = 'System Events'

    def __str__(self):
        return f"{self.event_type}: {self.title}"

    def mark_resolved(self, user=None):
        """Mark the event as resolved"""
        self.resolved = True
        self.resolved_at = timezone.now()
        if user:
            self.resolved_by = user
        self.save()
