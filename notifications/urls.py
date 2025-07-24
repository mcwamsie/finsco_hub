from django.urls import path, include
from . import views

app_name = 'notifications'

# Web URLs
web_patterns = [
    path('', views.notification_list, name='list'),
    path('<int:notification_id>/', views.notification_detail, name='detail'),
    path('<int:notification_id>/read/', views.mark_as_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_read'),
    path('preferences/', views.notification_preferences, name='preferences'),
    path('create/', views.create_notification_view, name='create'),
]

# API URLs
api_patterns = [
    path('list/', views.NotificationListAPIView.as_view(), name='api_list'),
    path('unread-count/', views.unread_count, name='api_unread_count'),
    path('recent/', views.recent_notifications, name='api_recent'),
    path('<int:notification_id>/read/', views.mark_notification_read_api, name='api_mark_read'),
    path('mark-all-read/', views.mark_all_read_api, name='api_mark_all_read'),
    path('types/', views.notification_types_api, name='api_types'),
    path('create/', views.create_notification_api, name='api_create'),
]

urlpatterns = [
    # Include web patterns at root level
    path('', include(web_patterns)),
    
    # Include API patterns under /api/
    path('api/', include(api_patterns)),
]