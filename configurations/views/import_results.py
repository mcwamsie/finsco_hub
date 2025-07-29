from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from configurations.models import ImportResult, ImportError, ImportSuccess


@login_required
def import_results_list(request):
    """Display list of import results"""
    results = ImportResult.objects.all().order_by('-created_at')
    
    # Filter by import type
    import_type = request.GET.get('import_type')
    if import_type:
        results = results.filter(import_type=import_type)
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        results = results.filter(status=status)
    
    # Filter by user
    user_id = request.GET.get('user')
    if user_id:
        results = results.filter(user_id=user_id)
    
    # Search
    search = request.GET.get('search')
    if search:
        results = results.filter(
            Q(original_filename__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(summary__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(results, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    import_types = ImportResult.IMPORT_TYPES
    statuses = ImportResult.STATUS_CHOICES
    
    context = {
        'page_obj': page_obj,
        'import_types': import_types,
        'statuses': statuses,
        'current_filters': {
            'import_type': import_type,
            'status': status,
            'user': user_id,
            'search': search,
        }
    }
    
    return render(request, 'configurations/import_results/list.html', context)


@login_required
def import_result_detail(request, result_id):
    """Display detailed view of an import result"""
    result = get_object_or_404(ImportResult, id=result_id)
    
    # Get errors with pagination
    errors = result.import_errors.all().order_by('row_number')
    error_paginator = Paginator(errors, 50)
    error_page = request.GET.get('error_page', 1)
    error_page_obj = error_paginator.get_page(error_page)
    
    # Get successes with pagination
    successes = result.import_successes.all().order_by('row_number')
    success_paginator = Paginator(successes, 50)
    success_page = request.GET.get('success_page', 1)
    success_page_obj = success_paginator.get_page(success_page)
    
    # Get error statistics
    error_stats = {}
    if errors.exists():
        from django.db.models import Count
        error_stats = errors.values('error_type').annotate(count=Count('id')).order_by('-count')
    
    context = {
        'result': result,
        'error_page_obj': error_page_obj,
        'success_page_obj': success_page_obj,
        'error_stats': error_stats,
        'show_errors': request.GET.get('tab') != 'successes',
    }
    
    return render(request, 'configurations/import_results/detail.html', context)


@login_required
@require_http_methods(["POST"])
def delete_import_result(request, result_id):
    """Delete an import result"""
    result = get_object_or_404(ImportResult, id=result_id)
    
    # Check permissions (you might want to add more specific permission checks)
    if not request.user.is_staff and result.user != request.user:
        messages.error(request, "You don't have permission to delete this import result.")
        return redirect('configurations:import_results_list')
    
    filename = result.original_filename
    result.delete()
    
    messages.success(request, f"Import result for '{filename}' has been deleted.")
    
    if request.headers.get('HX-Request'):
        return JsonResponse({'success': True, 'message': f"Import result for '{filename}' has been deleted."})
    
    return redirect('configurations:import_results_list')


@login_required
def import_result_errors_export(request, result_id):
    """Export import errors as CSV"""
    result = get_object_or_404(ImportResult, id=result_id)
    errors = result.import_errors.all().order_by('row_number')
    
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="import_errors_{result.id}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Row Number', 'Error Type', 'Field Name', 'Error Message', 'Row Data'])
    
    for error in errors:
        row_data_str = ', '.join([f"{k}: {v}" for k, v in error.row_data.items()]) if error.row_data else ''
        writer.writerow([
            error.row_number,
            error.get_error_type_display(),
            error.field_name,
            error.error_message,
            row_data_str
        ])
    
    return response


@login_required
def import_dashboard(request):
    """Dashboard showing import statistics"""
    from django.db.models import Count, Avg
    from django.utils import timezone
    from datetime import timedelta
    
    # Recent imports (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_imports = ImportResult.objects.filter(created_at__gte=thirty_days_ago)
    
    # Statistics
    stats = {
        'total_imports': ImportResult.objects.count(),
        'recent_imports': recent_imports.count(),
        'successful_imports': recent_imports.filter(status='completed').count(),
        'failed_imports': recent_imports.filter(status='failed').count(),
        'partial_imports': recent_imports.filter(status='partial').count(),
    }
    
    # Import type breakdown
    import_type_stats = recent_imports.values('import_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Recent import results
    recent_results = ImportResult.objects.order_by('-created_at')[:10]
    
    # Average success rate
    completed_imports = recent_imports.exclude(total_rows=0)
    if completed_imports.exists():
        avg_success_rate = completed_imports.aggregate(
            avg_rate=Avg('successful_rows') * 100.0 / Avg('total_rows')
        )['avg_rate'] or 0
    else:
        avg_success_rate = 0
    
    context = {
        'stats': stats,
        'import_type_stats': import_type_stats,
        'recent_results': recent_results,
        'avg_success_rate': round(avg_success_rate, 2),
    }
    
    return render(request, 'configurations/import_results/dashboard.html', context)