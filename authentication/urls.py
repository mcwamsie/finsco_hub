from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.LoginTemplateView.as_view(), name='login'),
    path('traditional-login/', views.CustomLoginView.as_view(), name='traditional_login'),
    path('email-login/', views.EmailLoginView.as_view(), name='email_login'),
    path('email-verify/', views.EmailVerificationView.as_view(), name='email_verify'),
    path('resend-code/', views.ResendCodeView.as_view(), name='resend_code'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]