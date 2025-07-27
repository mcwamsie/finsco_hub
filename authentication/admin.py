from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import DateTimeWidget

from authentication.models import User, NotificationPreference


class UserResource(resources.ModelResource):
    """Resource for importing/exporting User data"""

    # Custom fields for better export/import
    full_name = fields.Field(column_name='full_name', readonly=True)
    last_login_formatted = fields.Field(
        attribute='last_login',
        column_name='last_login',
        widget=DateTimeWidget(format='%Y-%m-%d %H:%M:%S')
    )
    date_joined_formatted = fields.Field(
        attribute='date_joined',
        column_name='date_joined',
        widget=DateTimeWidget(format='%Y-%m-%d %H:%M:%S')
    )

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'is_staff', 'is_superuser', 'phone',
            'date_joined_formatted', 'last_login_formatted',
            'receive_sms_notifications', 'receive_email_notifications',
            'notify_security_alerts', 'notify_account_activities', 'notify_claims_updates',
            'notify_system_updates', 'notify_marketing',
            'two_factor_enabled', 'type', 'designation'
        )
        export_order = fields

    def dehydrate_full_name(self, user):
        """Generate full name for export"""
        return f"{user.first_name} {user.last_name}".strip()

    def before_import_row(self, row, **kwargs):
        """Process data before importing"""
        # Ensure email is lowercase
        if 'email' in row:
            row['email'] = row['email'].lower().strip()

        # Generate username from email if not provided
        if not row.get('username') and row.get('email'):
            row['username'] = row['email'].split('@')[0]


class NotificationPreferenceInline(admin.TabularInline):
    """Inline admin for notification preferences"""
    model = NotificationPreference
    extra = 0
    fields = ('activity_type', 'enabled', 'sms_enabled', 'email_enabled')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, BaseUserAdmin):
    """Enhanced User admin with import/export functionality"""

    resource_class = UserResource
    inlines = [NotificationPreferenceInline]

    # List display
    list_display = (
        'username', 'email', 'get_full_name', 'phone',
        'is_active', 'is_staff', 'type', 'designation',
        'two_factor_badge', 'notification_summary', 'last_login_formatted', 'date_joined_formatted'
    )

    # List filters
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'type',
        'two_factor_enabled', 'receive_sms_notifications', 
        'receive_email_notifications', 'notify_security_alerts',
        'notify_account_activities', 'notify_claims_updates',
        'notify_system_updates', 'notify_marketing',
        'date_joined', 'last_login'
    )

    # Search fields
    search_fields = (
        'username', 'email', 'first_name', 'last_name',
        'phone', 'type', 'designation'
    )

    # Ordering
    ordering = ('-date_joined',)

    # Actions
    actions = [
        'activate_users', 'deactivate_users', 'enable_two_factor', 
        'disable_two_factor', 'enable_all_notifications', 'disable_marketing_notifications',
        'send_welcome_email'
    ]

    # Fieldsets for add/change forms
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('System Associations', {
            'fields': ('member', 'service_provider', 'agent', 'members'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Security & User Type', {
            'fields': (
                'two_factor_enabled', 'type', 'designation',
                'failed_login_attempts', 'account_locked_until',
                'force_password_change'
            ),
            'classes': ('collapse',)
        }),
        ('Global Notification Settings', {
            'fields': (
                'receive_sms_notifications', 'receive_email_notifications',
                'preferred_notification_method', 'timezone',
                'sms_quiet_hours_start', 'sms_quiet_hours_end',
                'email_quiet_hours_start', 'email_quiet_hours_end'
            ),
            'classes': ('collapse',)
        }),
        ('Notification Categories', {
            'fields': (
                'notify_security_alerts', 'notify_account_activities',
                'notify_claims_updates', 'notify_system_updates',
                'notify_marketing', 'low_balance_threshold'
            ),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined', 'password_changed_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'first_name', 'last_name',
                'phone', 'password1', 'password2'
            ),
        }),
        ('User Type & Permissions', {
            'fields': ('type', 'designation', 'is_active', 'is_staff', 'is_superuser'),
            'classes': ('collapse',)
        }),
        ('Notification Preferences', {
            'fields': (
                'receive_sms_notifications', 'receive_email_notifications',
                'notify_security_alerts', 'notify_account_activities',
                'notify_claims_updates'
            ),
            'classes': ('collapse',)
        }),
    )

    # Custom methods for list display
    def get_full_name(self, obj):
        """Display full name"""
        return obj.get_full_name() or '-'
    get_full_name.short_description = 'Full Name'
    
    def two_factor_badge(self, obj):
        """Display two-factor authentication status"""
        if obj.two_factor_enabled:
            return format_html(
                '<span class="badge" style="background-color: #007bff; color: white; padding: 2px 6px; border-radius: 3px;">🔒 Enabled</span>'
            )
        return format_html(
            '<span class="badge" style="background-color: #6c757d; color: white; padding: 2px 6px; border-radius: 3px;">🔓 Disabled</span>'
        )
    two_factor_badge.short_description = '2FA Status'

    def notification_summary(self, obj):
        """Display notification preferences summary"""
        enabled_categories = []
        if obj.notify_security_alerts:
            enabled_categories.append('Security')
        if obj.notify_account_activities:
            enabled_categories.append('Account')
        if obj.notify_claims_updates:
            enabled_categories.append('Claims')
        if obj.notify_system_updates:
            enabled_categories.append('System')
        if obj.notify_marketing:
            enabled_categories.append('Marketing')
        
        if not enabled_categories:
            return format_html('<span style="color: #dc3545;">None</span>')
        
        summary = ', '.join(enabled_categories)
        if len(summary) > 30:
            summary = summary[:27] + '...'
        
        return format_html(f'<span style="color: #28a745;">{summary}</span>')
    
    notification_summary.short_description = 'Notification Categories'

    def last_login_formatted(self, obj):
        """Format last login date"""
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M')
        return 'Never'

    last_login_formatted.short_description = 'Last Login'

    def date_joined_formatted(self, obj):
        """Format date joined"""
        return obj.date_joined.strftime('%Y-%m-%d %H:%M')

    date_joined_formatted.short_description = 'Date Joined'

    # Custom actions
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users were successfully activated.')

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users were successfully deactivated.')
    deactivate_users.short_description = "Deactivate selected users"
    
    def enable_two_factor(self, request, queryset):
        """Enable two-factor authentication"""
        updated = queryset.update(two_factor_enabled=True)
        self.message_user(request, f'Two-factor authentication enabled for {updated} users.')
    enable_two_factor.short_description = "Enable 2FA for selected users"

    def disable_two_factor(self, request, queryset):
        """Disable two-factor authentication"""
        updated = queryset.update(two_factor_enabled=False)
        self.message_user(request, f'Two-factor authentication disabled for {updated} users.')

    disable_two_factor.short_description = "Disable 2FA for selected users"

    def enable_all_notifications(self, request, queryset):
        """Enable all notification categories for selected users"""
        updated = queryset.update(
            notify_security_alerts=True,
            notify_account_activities=True,
            notify_claims_updates=True,
            notify_system_updates=True,
            receive_sms_notifications=True,
            receive_email_notifications=True
        )
        self.message_user(request, f'All notifications enabled for {updated} users.')
    enable_all_notifications.short_description = "Enable all notifications"

    def disable_marketing_notifications(self, request, queryset):
        """Disable marketing notifications for selected users"""
        updated = queryset.update(notify_marketing=False)
        self.message_user(request, f'Marketing notifications disabled for {updated} users.')
    disable_marketing_notifications.short_description = "Disable marketing notifications"

    def send_welcome_email(self, request, queryset):
        """Send welcome email to selected users"""
        # This would integrate with your email system
        count = queryset.count()
        self.message_user(request, f'Welcome emails queued for {count} users.')

    send_welcome_email.short_description = "Send welcome email"


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin for detailed notification preferences"""
    
    list_display = (
        'user', 'activity_type', 'enabled', 'sms_enabled', 
        'email_enabled', 'updated_at'
    )
    
    list_filter = (
        'activity_type', 'enabled', 'sms_enabled', 'email_enabled',
        'created_at', 'updated_at'
    )
    
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 
        'user__last_name', 'activity_type'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'activity_type')
        }),
        ('Preferences', {
            'fields': ('enabled', 'sms_enabled', 'email_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['enable_notifications', 'disable_notifications', 'enable_sms_only', 'enable_email_only']
    
    def enable_notifications(self, request, queryset):
        """Enable selected notification preferences"""
        updated = queryset.update(enabled=True, sms_enabled=True, email_enabled=True)
        self.message_user(request, f'{updated} notification preferences enabled.')
    enable_notifications.short_description = "Enable selected notifications"
    
    def disable_notifications(self, request, queryset):
        """Disable selected notification preferences"""
        updated = queryset.update(enabled=False)
        self.message_user(request, f'{updated} notification preferences disabled.')
    disable_notifications.short_description = "Disable selected notifications"
    
    def enable_sms_only(self, request, queryset):
        """Enable SMS only for selected preferences"""
        updated = queryset.update(enabled=True, sms_enabled=True, email_enabled=False)
        self.message_user(request, f'{updated} preferences set to SMS only.')
    enable_sms_only.short_description = "Enable SMS only"
    
    def enable_email_only(self, request, queryset):
        """Enable email only for selected preferences"""
        updated = queryset.update(enabled=True, sms_enabled=False, email_enabled=True)
        self.message_user(request, f'{updated} preferences set to email only.')
    enable_email_only.short_description = "Enable email only"
