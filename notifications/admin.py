from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from .models import NotificationType, Notification, NotificationLog


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'priority', 'is_active',
        'default_channels', 'created_at'
    ]
    list_filter = ['category', 'priority', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'priority', 'is_active')
        }),
        ('Default Channel Settings', {
            'fields': ('default_email_enabled', 'default_push_enabled')
        }),
    )

    def default_channels(self, obj):
        channels = []
        if obj.default_email_enabled:
            channels.append('📧 Email')
        if obj.default_push_enabled:
            channels.append('🔔 Push')
        return ' | '.join(channels) if channels else 'None'
    default_channels.short_description = 'Default Channels'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'notification_type', 'created_at',
        'delivery_status', 'is_read_display'
    ]
    list_filter = [
        'notification_type__category', 'notification_type',
        'email_sent', 'sms_sent', 'push_sent', 'is_read',
        'created_at'
    ]
    search_fields = [
        'title', 'message', 'user__username', 'user__email'
    ]
    readonly_fields = [
        'created_at', 'read_at', 'email_delivered', 'sms_delivered', 'push_delivered'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'notification_type', 'title', 'message')
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Delivery Status', {
            'fields': (
                ('email_sent', 'email_delivered'),
                ('sms_sent', 'sms_delivered'),
                ('push_sent', 'push_delivered'),
            )
        }),
        ('Reading Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Error Messages', {
            'fields': ('email_error', 'sms_error', 'push_error'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def delivery_status(self, obj):
        statuses = []
        
        # Email status
        if obj.email_sent and obj.email_delivered:
            statuses.append('📧✅')
        elif obj.email_sent and not obj.email_delivered:
            statuses.append('📧⏳')
        elif obj.email_error:
            statuses.append('📧❌')
        
        # SMS status
        if obj.sms_sent and obj.sms_delivered:
            statuses.append('📱✅')
        elif obj.sms_sent and not obj.sms_delivered:
            statuses.append('📱⏳')
        elif obj.sms_error:
            statuses.append('📱❌')
        
        # Push status
        if obj.push_sent and obj.push_delivered:
            statuses.append('🔔✅')
        elif obj.push_sent and not obj.push_delivered:
            statuses.append('🔔⏳')
        elif obj.push_error:
            statuses.append('🔔❌')
        
        return ' '.join(statuses) if statuses else '❌'
    delivery_status.short_description = 'Delivery Status'

    def is_read_display(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        else:
            return format_html('<span style="color: orange;">Unread</span>')
    is_read_display.short_description = 'Read Status'

    actions = ['mark_as_read', 'retry_failed']

    def mark_as_read(self, request, queryset):
        updated = 0
        for notification in queryset:
            if not notification.is_read:
                notification.mark_as_read()
                updated += 1
        
        self.message_user(
            request,
            f"{updated} notification(s) marked as read."
        )
    mark_as_read.short_description = "Mark selected notifications as read"

    def retry_failed(self, request, queryset):
        # Reset failed notifications for retry
        updated = 0
        for notification in queryset:
            if notification.email_error or notification.sms_error or notification.push_error:
                notification.email_sent = False
                notification.sms_sent = False
                notification.push_sent = False
                notification.email_error = ''
                notification.sms_error = ''
                notification.push_error = ''
                notification.save()
                updated += 1
        
        self.message_user(
            request,
            f"{updated} failed notification(s) reset for retry."
        )
    retry_failed.short_description = "Reset failed notifications for retry"


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'notification', 'channel', 'status', 'sent_at',
        'delivered_at', 'provider'
    ]
    list_filter = [
        'channel', 'status', 'created_at', 'provider'
    ]
    search_fields = [
        'notification__title', 'provider_message_id', 'error_message'
    ]
    readonly_fields = [
        'notification', 'channel', 'status', 'sent_at',
        'delivered_at', 'provider', 'provider_message_id',
        'error_code', 'error_message', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
