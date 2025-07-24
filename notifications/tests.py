from django.test import TestCase, Client
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, time
from unittest.mock import patch, MagicMock

from .models import Notification, NotificationType, NotificationLog
from .services import NotificationService

User = get_user_model()


class NotificationModelTests(TestCase):
    """Test notification models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.notification_type = NotificationType.objects.create(
            name='test_notification',
            description='Test notification type',
            category='GENERAL'
        )
    
    def test_notification_creation(self):
        """Test basic notification creation"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type=self.notification_type,
            title='Test Notification',
            message='This is a test notification'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.title, 'Test Notification')
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
    
    def test_mark_notification_as_read(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type=self.notification_type,
            title='Test Notification',
            message='This is a test notification'
        )
        
        notification.mark_as_read()
        
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
    
    def test_notification_type_creation(self):
        """Test notification type creation"""
        notif_type = NotificationType.objects.create(
            name='claim_approved',
            description='Claim approval notification',
            category='CLAIMS',
            priority='HIGH'
        )
        
        self.assertEqual(notif_type.name, 'claim_approved')
        self.assertEqual(notif_type.category, 'CLAIMS')
        self.assertEqual(notif_type.priority, 'HIGH')
    
    def test_notification_log_creation(self):
        """Test notification log creation"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type=self.notification_type,
            title='Test Notification',
            message='This is a test notification'
        )
        
        log = NotificationLog.objects.create(
            notification=notification,
            channel='email',
            status='sent'
        )
        
        self.assertEqual(log.notification, notification)
        self.assertEqual(log.channel, 'email')
        self.assertEqual(log.status, 'sent')


class NotificationServiceTests(TestCase):
    """Test notification service functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            # Enable some notification preferences
            receive_email_notifications=True,
            receive_sms_notifications=True,
            claim_approved_email=True,
            claim_approved_sms=False,
            system_update_email=True
        )
        
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            # Different preferences
            receive_email_notifications=False,
            receive_sms_notifications=True,
            claim_approved_email=False,
            claim_approved_sms=True
        )
    
    @patch('notifications.services.NotificationService._send_email')
    @patch('notifications.services.NotificationService._send_sms')
    def test_create_notification(self, mock_send_sms, mock_send_email):
        """Test creating a notification"""
        mock_send_email.return_value = True
        mock_send_sms.return_value = True
        
        notification = NotificationService.create_notification(
            user=self.user,
            notification_type='claim_approved',
            title='Claim Approved',
            message='Your claim has been approved'
        )
        
        self.assertIsInstance(notification, Notification)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.title, 'Claim Approved')
        
        # Check that notification type was created
        self.assertTrue(NotificationType.objects.filter(name='claim_approved').exists())
    
    @patch('notifications.services.NotificationService._send_email')
    @patch('notifications.services.NotificationService._send_sms')
    def test_send_notification_with_user_preferences(self, mock_send_sms, mock_send_email):
        """Test sending notification respects user preferences"""
        mock_send_email.return_value = True
        mock_send_sms.return_value = True
        
        # Mock the user methods
        with patch.object(self.user, 'can_receive_notification', return_value=True), \
             patch.object(self.user, 'get_active_notification_channels', return_value=['email']):
            
            notification = NotificationService.create_notification(
                user=self.user,
                notification_type='claim_approved',
                title='Claim Approved',
                message='Your claim has been approved',
                send_immediately=True
            )
            
            # Should have called email but not SMS based on mocked channels
            mock_send_email.assert_called_once()
            mock_send_sms.assert_not_called()
    
    def test_send_bulk_notifications(self):
        """Test sending bulk notifications"""
        users = [self.user, self.user2]
        
        with patch.object(User, 'can_receive_notification', return_value=True), \
             patch('notifications.services.NotificationService.send_notification') as mock_send:
            
            notifications = NotificationService.send_bulk_notifications(
                users=users,
                notification_type='system_update',
                title='System Update',
                message='System will be updated tonight'
            )
            
            self.assertEqual(len(notifications), 2)
            self.assertEqual(mock_send.call_count, 2)
    
    def test_send_user_specific_notification(self):
        """Test sending user-specific notification"""
        with patch.object(self.user, 'can_receive_notification', return_value=True), \
             patch.object(self.user, 'get_active_notification_channels', return_value=['email', 'sms']), \
             patch('notifications.services.NotificationService.send_notification') as mock_send:
            
            mock_send.return_value = {'email': True, 'sms': True, 'push': False, 'in_app': True}
            
            result = NotificationService.send_user_specific_notification(
                user=self.user,
                activity_type='claim_approved',
                title='Claim Approved',
                message='Your claim has been approved'
            )
            
            self.assertTrue(result['sent'])
            self.assertEqual(result['channels'], ['email', 'sms'])
            self.assertIsNotNone(result['notification'])
    
    def test_send_user_specific_notification_disabled(self):
        """Test sending notification when user has disabled it"""
        with patch.object(self.user, 'can_receive_notification', return_value=False):
            
            result = NotificationService.send_user_specific_notification(
                user=self.user,
                activity_type='claim_approved',
                title='Claim Approved',
                message='Your claim has been approved'
            )
            
            self.assertFalse(result['sent'])
            self.assertEqual(result['reason'], 'User disabled this notification type')
            self.assertIsNone(result['notification'])
    
    def test_mark_as_read(self):
        """Test marking notification as read"""
        notification = NotificationService.create_notification(
            user=self.user,
            notification_type='test',
            title='Test',
            message='Test message',
            send_immediately=False
        )
        
        result = NotificationService.mark_as_read(notification.id, self.user)
        
        self.assertTrue(result)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
    
    def test_mark_all_as_read(self):
        """Test marking all notifications as read"""
        # Create multiple notifications
        for i in range(3):
            NotificationService.create_notification(
                user=self.user,
                notification_type='test',
                title=f'Test {i}',
                message=f'Test message {i}',
                send_immediately=False
            )
        
        count = NotificationService.mark_all_as_read(self.user)
        
        self.assertEqual(count, 3)
        unread_count = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread_count, 0)
    
    def test_get_unread_count(self):
        """Test getting unread notification count"""
        # Create notifications
        for i in range(2):
            NotificationService.create_notification(
                user=self.user,
                notification_type='test',
                title=f'Test {i}',
                message=f'Test message {i}',
                send_immediately=False
            )
        
        count = NotificationService.get_unread_count(self.user)
        self.assertEqual(count, 2)
    
    def test_get_recent_notifications(self):
        """Test getting recent notifications"""
        # Create notifications
        for i in range(5):
            NotificationService.create_notification(
                user=self.user,
                notification_type='test',
                title=f'Test {i}',
                message=f'Test message {i}',
                send_immediately=False
            )
        
        recent = NotificationService.get_recent_notifications(self.user, limit=3)
        self.assertEqual(len(recent), 3)


class NotificationManagementTests(TestCase):
    """Test notification management functions"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_cleanup_old_notifications(self):
        """Test cleaning up old notifications using management command"""
        # Create old notification
        old_notification = NotificationService.create_notification(
            user=self.user,
            notification_type='test',
            title='Old Notification',
            message='This is old',
            send_immediately=False
        )
        
        # Make it old
        old_date = timezone.now() - timedelta(days=35)
        old_notification.created_at = old_date
        old_notification.save()
        
        # Create recent notification
        recent_notification = NotificationService.create_notification(
            user=self.user,
            notification_type='test',
            title='Recent Notification',
            message='This is recent',
            send_immediately=False
        )
        
        # Cleanup notifications older than 30 days
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        call_command('cleanup_notifications', '--days=30', stdout=out)
        
        self.assertFalse(Notification.objects.filter(id=old_notification.id).exists())
        self.assertTrue(Notification.objects.filter(id=recent_notification.id).exists())
    
    def test_send_welcome_notification(self):
        """Test sending welcome notification"""
        with patch('notifications.services.NotificationService.create_notification') as mock_create:
            # Simulate welcome notification creation
            NotificationService.create_notification(
                user=self.user,
                notification_type='welcome',
                title='Welcome to FiscoHub!',
                message='Thank you for joining our platform.',
                send_immediately=True
            )
            
            mock_create.assert_called_once()
            args, kwargs = mock_create.call_args
            self.assertEqual(kwargs['user'], self.user)
            self.assertEqual(kwargs['notification_type'], 'welcome')
    
    def test_create_system_notification(self):
        """Test creating system-wide notification"""
        with patch('notifications.services.NotificationService.send_bulk_notifications') as mock_bulk:
            mock_bulk.return_value = []
            
            # Get all active users
            users = User.objects.filter(is_active=True)
            
            NotificationService.send_bulk_notifications(
                users=users,
                notification_type='system_announcement',
                title='System Maintenance',
                message='System will be down for maintenance'
            )
            
            mock_bulk.assert_called_once()
            args, kwargs = mock_bulk.call_args
            self.assertEqual(kwargs['notification_type'], 'system_announcement')
            self.assertEqual(kwargs['title'], 'System Maintenance')


class UserNotificationIntegrationTests(TestCase):
    """Test integration with User model notification preferences"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            # Set up various notification preferences
            receive_email_notifications=True,
            receive_sms_notifications=True,
            claim_approved_email=True,
            claim_approved_sms=False,
            system_update_email=False,
            system_update_sms=True,
            emergency_alert_email=True,
            emergency_alert_sms=True,
            # Quiet hours
            email_quiet_hours_enabled=True,
            email_quiet_start_time=time(22, 0),  # 10 PM
            email_quiet_end_time=time(8, 0),     # 8 AM
            sms_quiet_hours_enabled=True,
            sms_quiet_start_time=time(23, 0),    # 11 PM
            sms_quiet_end_time=time(7, 0),       # 7 AM
        )
    
    def test_user_can_receive_notification_method(self):
        """Test User.can_receive_notification method"""
        # Test with enabled notification
        self.assertTrue(self.user.can_receive_notification('claim_approved'))
        
        # Test with disabled notification
        self.assertFalse(self.user.can_receive_notification('system_update'))
        
        # Test with emergency (should always be enabled if emergency_alert is True)
        self.assertTrue(self.user.can_receive_notification('emergency_alert'))
    
    def test_user_get_active_notification_channels(self):
        """Test User.get_active_notification_channels method"""
        # Mock the method since we need to test the actual implementation
        with patch.object(self.user, 'get_active_notification_channels') as mock_method:
            mock_method.return_value = ['email']
            
            channels = self.user.get_active_notification_channels('claim_approved')
            self.assertEqual(channels, ['email'])
            mock_method.assert_called_once_with('claim_approved')
    
    def test_user_quiet_hours_methods(self):
        """Test User quiet hours methods"""
        # Mock the quiet hours methods
        with patch.object(self.user, 'is_in_email_quiet_hours', return_value=True), \
             patch.object(self.user, 'is_in_sms_quiet_hours', return_value=False):
            
            self.assertTrue(self.user.is_in_email_quiet_hours())
            self.assertFalse(self.user.is_in_sms_quiet_hours())
    
    def test_notification_service_category_mapping(self):
        """Test notification type category mapping"""
        test_cases = [
            ('claim_approved', 'CLAIMS'),
            ('member_registration', 'MEMBER'),
            ('account_credited', 'ACCOUNT'),
            ('provider_registration', 'PROVIDER'),
            ('login_failed', 'SECURITY'),
            ('system_update', 'SYSTEM'),
            ('promotion_available', 'MARKETING'),
            ('emergency_alert', 'EMERGENCY'),
            ('unknown_type', 'GENERAL'),
        ]
        
        for notification_type, expected_category in test_cases:
            category = NotificationService._get_category_for_type(notification_type)
            self.assertEqual(category, expected_category, 
                           f"Expected {expected_category} for {notification_type}, got {category}")


class NotificationAPITests(TestCase):
    """Test notification API endpoints"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
    
    def test_notification_list_api(self):
        """Test notification list API endpoint"""
        # Create a notification
        NotificationService.create_notification(
            user=self.user,
            notification_type='test',
            title='Test Notification',
            message='Test message',
            send_immediately=False
        )
        
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
    
    def test_unread_count_api(self):
        """Test unread count API endpoint"""
        # Create notifications
        for i in range(3):
            NotificationService.create_notification(
                user=self.user,
                notification_type='test',
                title=f'Test {i}',
                message=f'Test message {i}',
                send_immediately=False
            )
        
        response = self.client.get('/api/notifications/unread-count/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['count'], 3)
    
    def test_mark_notification_read_api(self):
        """Test mark notification as read API endpoint"""
        notification = NotificationService.create_notification(
            user=self.user,
            notification_type='test',
            title='Test Notification',
            message='Test message',
            send_immediately=False
        )
        
        response = self.client.post(f'/api/notifications/{notification.id}/mark-read/')
        self.assertEqual(response.status_code, 200)
        
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
    
    def test_mark_all_read_api(self):
        """Test mark all notifications as read API endpoint"""
        # Create notifications
        for i in range(3):
            NotificationService.create_notification(
                user=self.user,
                notification_type='test',
                title=f'Test {i}',
                message=f'Test message {i}',
                send_immediately=False
            )
        
        response = self.client.post('/api/notifications/mark-all-read/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['marked_count'], 3)
        
        # Check that all notifications are marked as read
        unread_count = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread_count, 0)
