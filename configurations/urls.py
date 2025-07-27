from django.urls import path
from . import views

app_name = 'configurations'

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]