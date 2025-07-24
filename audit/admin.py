from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import AuditLog, LoginAttempt, DataExport, SystemEvent
import json


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'user', 'action', 'object_repr', 
        'module', 'ip_address', 'changes_summary'
    ]
    list_filter = [
        'action', 'timestamp', 'module', 'content_type'
    ]
    search_fields = [
        'user__username', 'user__email', 'object_repr', 
        'ip_address', 'module'
    ]
    readonly_fields = [
        'user', 'action', 'content_type', 'object_id', 
        'object_repr', 'changes', 'timestamp', 'ip_address',
        'user_agent', 'session_key', 'module', 'changes_display'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'action', 'timestamp', 'module')
        }),
        ('Object Details', {
            'fields': ('content_type', 'object_id', 'object_repr')
        }),
        ('Changes', {
            'fields': ('changes_display', 'reason'),
            'classes': ('collapse',)
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent', 'session_key'),
            'classes': ('collapse',)
        }),
    )

    def changes_summary(self, obj):
        if not obj.changes:
            return "No changes"
        return f"{len(obj.changes)} field(s) changed"
    changes_summary.short_description = "Changes"

    def changes_display(self, obj):
        if not obj.changes:
            return "No changes recorded"
        
        formatted_changes = []
        for field, change in obj.changes.items():
            if isinstance(change, dict) and 'old' in change and 'new' in change:
                formatted_changes.append(
                    f"<strong>{field}:</strong> '{change['old']}' → '{change['new']}'"
                )
            else:
                formatted_changes.append(f"<strong>{field}:</strong> {change}")
        
        return mark_safe("<br>".join(formatted_changes))
    changes_display.short_description = "Changes Detail"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'username', 'status', 'ip_address', 
        'country', 'city', 'failure_reason'
    ]
    list_filter = [
        'status', 'timestamp', 'country'
    ]
    search_fields = [
        'username', 'ip_address', 'country', 'city'
    ]
    readonly_fields = [
        'username', 'status', 'ip_address', 'user_agent',
        'timestamp', 'failure_reason', 'country', 'city'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(DataExport)
class DataExportAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'user', 'export_type', 'file_format',
        'record_count', 'file_size_display', 'download_count'
    ]
    list_filter = [
        'export_type', 'file_format', 'timestamp'
    ]
    search_fields = [
        'user__username', 'user__email', 'export_type'
    ]
    readonly_fields = [
        'user', 'export_type', 'file_format', 'record_count',
        'file_size', 'filters_applied', 'timestamp', 'ip_address',
        'file_path', 'download_count', 'filters_display'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    fieldsets = (
        ('Export Information', {
            'fields': ('user', 'export_type', 'file_format', 'timestamp')
        }),
        ('Data Details', {
            'fields': ('record_count', 'file_size', 'filters_display')
        }),
        ('File Information', {
            'fields': ('file_path', 'download_count'),
            'classes': ('collapse',)
        }),
        ('Technical Details', {
            'fields': ('ip_address',),
            'classes': ('collapse',)
        }),
    )

    def file_size_display(self, obj):
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = "File Size"

    def filters_display(self, obj):
        if not obj.filters_applied:
            return "No filters applied"
        
        formatted_filters = []
        for key, value in obj.filters_applied.items():
            formatted_filters.append(f"<strong>{key}:</strong> {value}")
        
        return mark_safe("<br>".join(formatted_filters))
    filters_display.short_description = "Filters Applied"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SystemEvent)
class SystemEventAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'event_type', 'title', 'module',
        'user', 'resolved', 'resolved_status'
    ]
    list_filter = [
        'event_type', 'resolved', 'timestamp', 'module'
    ]
    search_fields = [
        'title', 'description', 'module', 'function_name',
        'user__username', 'error_code'
    ]
    readonly_fields = [
        'event_type', 'title', 'description', 'module',
        'function_name', 'line_number', 'error_code',
        'stack_trace', 'user', 'ip_address', 'timestamp'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    fieldsets = (
        ('Event Information', {
            'fields': ('event_type', 'title', 'description', 'timestamp')
        }),
        ('Technical Details', {
            'fields': ('module', 'function_name', 'line_number', 'error_code'),
            'classes': ('collapse',)
        }),
        ('Error Details', {
            'fields': ('stack_trace',),
            'classes': ('collapse',)
        }),
        ('Context', {
            'fields': ('user', 'ip_address')
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolved_at', 'resolved_by')
        }),
    )

    def resolved_status(self, obj):
        if obj.resolved:
            return format_html(
                '<span style="color: green;">✓ Resolved</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ Unresolved</span>'
            )
    resolved_status.short_description = "Status"

    actions = ['mark_resolved']

    def mark_resolved(self, request, queryset):
        updated = queryset.filter(resolved=False).update(
            resolved=True,
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(
            request,
            f"{updated} event(s) marked as resolved."
        )
    mark_resolved.short_description = "Mark selected events as resolved"
