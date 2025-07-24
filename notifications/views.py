from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import get_user_model

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView

from .models import Notification, NotificationType
from .signals import create_notification
from .serializers import (
    NotificationSerializer,
    NotificationTypeSerializer,
    CreateNotificationSerializer
)
from .services import NotificationService

User = get_user_model()


@login_required
def notification_list(request):
    """Display user's notifications with filtering and pagination."""
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related('notification_type').order_by('-created_at')
    
    # Filter by read status
    status_filter = request.GET.get('status')
    if status_filter == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status_filter == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Filter by notification type
    type_filter = request.GET.get('type')
    if type_filter:
        notifications = notifications.filter(notification_type__name=type_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get notification types for filter dropdown
    notification_types = NotificationType.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'notification_types': notification_types,
        'current_status': status_filter,
        'current_type': type_filter,
        'search_query': search_query,
    }
    
    return render(request, 'notifications/notification_list.html', context)


@login_required
@require_http_methods(["POST"])
def mark_as_read(request, notification_id):
    """Mark a specific notification as read."""
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    
    if not notification.is_read:
        notification.mark_as_read()
        return JsonResponse({'status': 'success', 'message': 'Notification marked as read'})
    
    return JsonResponse({'status': 'info', 'message': 'Notification already read'})


@login_required
@require_http_methods(["POST"])
def mark_all_as_read(request):
    """Mark all user's notifications as read."""
    count = NotificationService.mark_all_as_read(request.user)
    
    return JsonResponse({
        'status': 'success',
        'message': f'{count} notifications marked as read'
    })


@login_required
def notification_detail(request, notification_id):
    """Display detailed view of a notification."""
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    
    # Mark as read when viewed
    if not notification.is_read:
        notification.mark_as_read()
    
    context = {
        'notification': notification,
    }
    
    return render(request, 'notifications/notification_detail.html', context)


@login_required
def notification_preferences(request):
    """Display and update user notification preferences using User model fields."""
    user = request.user
    
    if request.method == 'POST':
        # Update user's notification preferences
        # This would update the User model's notification fields
        # Example implementation - you can customize based on your needs
        
        # Global settings
        user.receive_email_notifications = request.POST.get('email_notifications') == 'on'
        user.receive_sms_notifications = request.POST.get('sms_notifications') == 'on'
        
        # Quiet hours
        user.sms_quiet_hours_enabled = request.POST.get('sms_quiet_hours_enabled') == 'on'
        user.email_quiet_hours_enabled = request.POST.get('email_quiet_hours_enabled') == 'on'
        
        if user.sms_quiet_hours_enabled:
            user.sms_quiet_hours_start = request.POST.get('sms_quiet_hours_start')
            user.sms_quiet_hours_end = request.POST.get('sms_quiet_hours_end')
        
        if user.email_quiet_hours_enabled:
            user.email_quiet_hours_start = request.POST.get('email_quiet_hours_start')
            user.email_quiet_hours_end = request.POST.get('email_quiet_hours_end')
        
        # Phone number for SMS
        user.phone_number = request.POST.get('phone_number', '')
        
        # Update specific notification preferences
        # You can add more fields based on your User model's notification fields
        user.notify_member_registration = request.POST.get('notify_member_registration') == 'on'
        user.notify_member_registration_sms = request.POST.get('notify_member_registration_sms') == 'on'
        user.notify_member_registration_email = request.POST.get('notify_member_registration_email') == 'on'
        
        user.save()
        
        messages.success(request, 'Notification preferences updated successfully!')
    
    # Get notification types for display
    notification_types = NotificationType.objects.filter(is_active=True)
    
    context = {
        'user': user,
        'notification_types': notification_types,
    }
    
    return render(request, 'notifications/preferences.html', context)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_count(request):
    """API endpoint to get unread notification count."""
    count = NotificationService.get_unread_count(request.user)
    return Response({'unread_count': count})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def recent_notifications(request):
    """API endpoint to get recent notifications for dropdown/widget."""
    limit = int(request.query_params.get('limit', 10))
    notifications = NotificationService.get_recent_notifications(request.user, limit)
    
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


# Admin/Staff views for creating notifications
@staff_member_required
def create_notification_view(request):
    """Admin view to create notifications manually."""
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        notification_type_name = request.POST.get('notification_type')
        title = request.POST.get('title')
        message = request.POST.get('message')
        
        try:
            recipient = User.objects.get(id=recipient_id)
            
            notification = create_notification(
                recipient=recipient,
                notification_type_name=notification_type_name,
                title=title,
                message=message
            )
            
            messages.success(request, f'Notification created successfully for {recipient.username}!')
            
        except Exception as e:
            messages.error(request, f'Error creating notification: {str(e)}')
    
    # Get data for form
    users = User.objects.filter(is_active=True).order_by('username')
    notification_types = NotificationType.objects.filter(is_active=True)
    
    context = {
        'users': users,
        'notification_types': notification_types,
    }
    
    return render(request, 'notifications/create_notification.html', context)


# API Views
class NotificationListAPIView(ListAPIView):
    """API endpoint to list user's notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user).select_related('notification_type')
        
        # Filtering
        filter_type = self.request.query_params.get('type')
        if filter_type:
            queryset = queryset.filter(notification_type__name=filter_type)
        
        filter_read = self.request.query_params.get('read')
        if filter_read == 'unread':
            queryset = queryset.filter(is_read=False)
        elif filter_read == 'read':
            queryset = queryset.filter(is_read=True)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(message__icontains=search)
            )
        
        return queryset.order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read_api(request, notification_id):
    """API endpoint to mark notification as read"""
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    
    if not notification.is_read:
        notification.mark_as_read()
        return Response({'status': 'success', 'message': 'Notification marked as read'})
    
    return Response({'status': 'info', 'message': 'Notification already read'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_read_api(request):
    """API endpoint to mark all notifications as read"""
    count = NotificationService.mark_all_as_read(request.user)
    
    return Response({
        'status': 'success',
        'message': f'{count} notifications marked as read'
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_types_api(request):
    """API endpoint to get available notification types"""
    types = NotificationType.objects.filter(is_active=True)
    serializer = NotificationTypeSerializer(types, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def create_notification_api(request):
    """API endpoint for staff to create notifications"""
    serializer = CreateNotificationSerializer(data=request.data)
    
    if serializer.is_valid():
        data = serializer.validated_data
        
        try:
            # Handle multiple users if user_ids provided
            user_ids = data.get('user_ids', [])
            if user_ids:
                users = User.objects.filter(id__in=user_ids)
                notifications = NotificationService.send_bulk_notifications(
                    users=users,
                    notification_type=data['notification_type'],
                    title=data['title'],
                    message=data['message']
                )
                return Response({
                    'success': True,
                    'message': f'Notifications sent to {len(notifications)} users',
                    'notification_count': len(notifications)
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'error': 'No user IDs provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
