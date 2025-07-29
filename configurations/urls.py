from django.urls import path
from configurations.views import dashboard
from configurations.views import import_results

app_name = 'configurations'

urlpatterns = [
    path('dashboard/', dashboard.DashboardView.as_view(), name='dashboard'),
    
    # Import Results URLs
    path('import-results/', import_results.import_results_list, name='import_results_list'),
    path('import-results/<int:pk>/', import_results.import_result_detail, name='import_result_detail'),
    path('import-results/<int:pk>/delete/', import_results.delete_import_result, name='delete_import_result'),
    path('import-results/<int:pk>/errors/export/', import_results.import_result_errors_export, name='import_result_errors_export'),
    path('import-dashboard/', import_results.import_dashboard, name='import_dashboard'),
]