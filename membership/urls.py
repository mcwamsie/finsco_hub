from django.urls import path
from . import views

app_name = 'membership'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Member URLs
    path('members/', views.MemberTemplateView.as_view(), name='members'),
    path('members/list/', views.MemberListView.as_view(), name='members_list'),
    path('members/create/', views.MemberCreateView.as_view(), name='members_create'),

    path('members/details/<str:membership_number>/', views.MemberDetailView.as_view(), name='members_detail'),
    path('members/update/<str:membership_number>/update/', views.MemberUpdateView.as_view(), name='members_update'),
    
    # HTMX endpoints
    path('htmx/member-search/', views.member_search_suggestions, name='member_search_suggestions'),
    path('htmx/member-stats/', views.member_quick_stats, name='member_quick_stats'),
    path('htmx/member/<str:membership_number>/toggle-status/', views.toggle_member_status, name='toggle_member_status'),
    
    # Beneficiary URLs
    path('beneficiaries/', views.BeneficiaryTemplateView.as_view(), name='beneficiaries'),
    path('beneficiaries/list/', views.BeneficiaryListView.as_view(), name='beneficiaries_list'),
    path('beneficiaries/create/', views.BeneficiaryCreateView.as_view(), name='beneficiaries_create'),
    path('beneficiaries/details/<uuid:pk>/', views.BeneficiaryDetailView.as_view(), name='beneficiaries_detail'),
    path('beneficiaries/update/<uuid:pk>/update/', views.BeneficiaryUpdateView.as_view(), name='beneficiaries_update'),
    
    # Beneficiary HTMX endpoints
    path('htmx/beneficiary-search/', views.beneficiary_search_suggestions, name='beneficiary_search_suggestions'),
    path('htmx/beneficiary-stats/', views.beneficiary_quick_stats, name='beneficiary_quick_stats'),
    path('htmx/beneficiary/<uuid:pk>/toggle-status/', views.toggle_beneficiary_status, name='toggle_beneficiary_status'),
    
    # TopUp URLs
    path('topups/', views.TopUpTemplateView.as_view(), name='topups'),
    path('topups/list/', views.TopUpListView.as_view(), name='topups_list'),
    path('topups/create/', views.TopUpCreateView.as_view(), name='topups_create'),
    path('topups/details/<uuid:pk>/', views.TopUpDetailView.as_view(), name='topups_detail'),
    path('topups/update/<uuid:pk>/update/', views.TopUpUpdateView.as_view(), name='topups_update'),
    
    # TopUp HTMX endpoints
    path('htmx/topup-search/', views.topup_search_suggestions, name='topup_search_suggestions'),
    path('htmx/topup-stats/', views.topup_quick_stats, name='topup_quick_stats'),
    path('htmx/topup/<uuid:pk>/toggle-status/', views.toggle_topup_status, name='toggle_topup_status'),
    
    # Applications
    path('applications/', views.ApplicationListView.as_view(), name='application_list'),
]