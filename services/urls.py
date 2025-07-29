from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Claims URLs
    path('claims/', views.ClaimTemplateView.as_view(), name='claims'),
    path('claims/list/', views.ClaimListView.as_view(), name='claims_list'),
    path('claims/create/', views.ClaimCreateView.as_view(), name='claims_create'),
    path('claims/details/<uuid:pk>/', views.ClaimDetailView.as_view(), name='claims_detail'),
    path('claims/update/<uuid:pk>/update/', views.ClaimUpdateView.as_view(), name='claims_update'),
    
    # Claims HTMX endpoints
    path('htmx/claim-search/', views.claim_search_suggestions, name='claim_search_suggestions'),
    path('htmx/claim-stats/', views.claim_quick_stats, name='claim_quick_stats'),
    path('htmx/claim/<uuid:pk>/toggle-status/', views.toggle_claim_status, name='toggle_claim_status'),
    
    # Import/Export endpoints
    path('htmx/claims-import/', views.claims_import, name='claims_import'),
    path('htmx/claims-export/', views.claims_export, name='claims_export'),
    path('claims/import-process/', views.claims_import_process, name='claims_import_process'),
    path('claims/export-process/', views.claims_export_process, name='claims_export_process'),
    path('claims/sample-template/', views.claims_sample_template, name='claims_sample_template'),
    
    # Service Requests URLs
    path('requests/', views.ServiceRequestTemplateView.as_view(), name='requests'),
    path('requests/list/', views.ServiceRequestListView.as_view(), name='requests_list'),
    path('requests/create/', views.ServiceRequestCreateView.as_view(), name='requests_create'),
    path('requests/details/<uuid:pk>/', views.ServiceRequestDetailView.as_view(), name='requests_detail'),
    path('requests/update/<uuid:pk>/update/', views.ServiceRequestUpdateView.as_view(), name='requests_update'),
    
    # Service Requests HTMX endpoints
    path('htmx/request-search/', views.service_request_search_suggestions, name='request_search_suggestions'),
    path('htmx/request-stats/', views.service_request_quick_stats, name='request_quick_stats'),
    path('htmx/request/<uuid:pk>/toggle-status/', views.toggle_service_request_status, name='toggle_service_request_status'),
    
    # Services URLs
    path('services/', views.ServiceTemplateView.as_view(), name='services'),
    path('services/list/', views.ServiceListView.as_view(), name='services_list'),
    path('services/create/', views.ServiceCreateView.as_view(), name='services_create'),
    path('services/details/<uuid:pk>/', views.ServiceDetailView.as_view(), name='services_detail'),
    path('services/update/<uuid:pk>/update/', views.ServiceUpdateView.as_view(), name='services_update'),
    
    # Services HTMX endpoints
    path('htmx/service-search/', views.service_search_suggestions, name='service_search_suggestions'),
    path('htmx/service-stats/', views.service_quick_stats, name='service_quick_stats'),
    path('htmx/service/<uuid:pk>/toggle-status/', views.toggle_service_status, name='toggle_service_status'),
    
    # Additional endpoints for dropdowns and autocomplete
    path('htmx/beneficiary-lookup/', views.beneficiary_lookup, name='beneficiary_lookup'),
    path('htmx/service-provider-lookup/', views.service_provider_lookup, name='service_provider_lookup'),
    path('htmx/service-lookup/', views.service_lookup, name='service_lookup'),
    
    # Adjudication endpoints
    path('htmx/adjudicate-claim/<uuid:pk>/', views.adjudicate_claim, name='adjudicate_claim'),
    path('htmx/approve-request/<uuid:pk>/', views.approve_service_request, name='approve_service_request'),
    path('htmx/decline-request/<uuid:pk>/', views.decline_service_request, name='decline_service_request'),
]