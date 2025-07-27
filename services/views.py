from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta

from .models.claim import Claim, ClaimServiceLine
from .models.service_request import ServiceRequest, ServiceRequestItem
from .models.adjudication import AdjudicationMessageCode
from configurations.models.service import Service, ServiceModifier, ServiceTierPrice


# Claim Views
@login_required
def claim_list(request):
    """List all claims with filtering and pagination"""
    claims = Claim.objects.select_related(
        'beneficiary', 'provider', 'service_request', 'user'
    ).prefetch_related('services')
    
    # Filtering
    status = request.GET.get('status')
    provider = request.GET.get('provider')
    beneficiary = request.GET.get('beneficiary')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')
    
    if status:
        claims = claims.filter(status=status)
    if provider:
        claims = claims.filter(provider_id=provider)
    if beneficiary:
        claims = claims.filter(beneficiary_id=beneficiary)
    if date_from:
        claims = claims.filter(start_date__gte=date_from)
    if date_to:
        claims = claims.filter(end_date__lte=date_to)
    if search:
        claims = claims.filter(
            Q(transaction_number__icontains=search) |
            Q(invoice_number__icontains=search) |
            Q(beneficiary__first_name__icontains=search) |
            Q(beneficiary__last_name__icontains=search) |
            Q(provider__name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(claims, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_claims': claims.count(),
        'total_claimed': claims.aggregate(Sum('claimed_amount'))['claimed_amount__sum'] or 0,
        'total_adjudicated': claims.aggregate(Sum('adjudicated_amount'))['adjudicated_amount__sum'] or 0,
        'pending_claims': claims.filter(status='N').count(),
        'approved_claims': claims.filter(status='A').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'status_choices': Claim.STATUS_CHOICES,
        'current_filters': {
            'status': status,
            'provider': provider,
            'beneficiary': beneficiary,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    }
    
    return render(request, 'pages/core/services/claims/list.html', context)


@login_required
def claim_detail(request, claim_id):
    """View claim details"""
    claim = get_object_or_404(
        Claim.objects.select_related(
            'beneficiary', 'provider', 'service_request', 'user'
        ).prefetch_related('services__service'),
        id=claim_id
    )
    
    context = {
        'claim': claim,
        'service_lines': claim.services.all(),
    }
    
    return render(request, 'pages/core/services/claims/detail.html', context)


@login_required
def claim_create(request):
    """Create a new claim"""
    if request.method == 'POST':
        # Handle claim creation logic here
        # This would typically involve form processing
        pass
    
    context = {
        'title': 'Create New Claim',
    }
    
    return render(request, 'pages/core/services/claims/form.html', context)


@login_required
def claim_edit(request, claim_id):
    """Edit an existing claim"""
    claim = get_object_or_404(Claim, id=claim_id)
    
    if request.method == 'POST':
        # Handle claim update logic here
        pass
    
    context = {
        'claim': claim,
        'title': f'Edit Claim {claim.transaction_number}',
    }
    
    return render(request, 'pages/core/services/claims/form.html', context)


# Service Request Views
@login_required
def service_request_list(request):
    """List all service requests with filtering and pagination"""
    requests = ServiceRequest.objects.select_related(
        'beneficiary', 'service_provider', 'referring_provider', 
        'requested_by', 'reviewed_by', 'approved_by'
    ).prefetch_related('items__service')
    
    # Filtering
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    provider = request.GET.get('provider')
    beneficiary = request.GET.get('beneficiary')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')
    
    if status:
        requests = requests.filter(status=status)
    if priority:
        requests = requests.filter(priority=priority)
    if provider:
        requests = requests.filter(service_provider_id=provider)
    if beneficiary:
        requests = requests.filter(beneficiary_id=beneficiary)
    if date_from:
        requests = requests.filter(requested_date__gte=date_from)
    if date_to:
        requests = requests.filter(requested_date__lte=date_to)
    if search:
        requests = requests.filter(
            Q(request_number__icontains=search) |
            Q(beneficiary__first_name__icontains=search) |
            Q(beneficiary__last_name__icontains=search) |
            Q(service_provider__name__icontains=search) |
            Q(chief_complaint__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(requests, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_requests': requests.count(),
        'pending_requests': requests.filter(status='P').count(),
        'approved_requests': requests.filter(status='A').count(),
        'declined_requests': requests.filter(status='D').count(),
        'total_estimated': requests.aggregate(Sum('estimated_amount'))['estimated_amount__sum'] or 0,
        'total_approved': requests.aggregate(Sum('approved_amount'))['approved_amount__sum'] or 0,
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'status_choices': ServiceRequest.STATUS_CHOICES,
        'priority_choices': ServiceRequest.PRIORITY_CHOICES,
        'current_filters': {
            'status': status,
            'priority': priority,
            'provider': provider,
            'beneficiary': beneficiary,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    }
    
    return render(request, 'pages/core/services/requests/list.html', context)


@login_required
def service_request_detail(request, request_id):
    """View service request details"""
    service_request = get_object_or_404(
        ServiceRequest.objects.select_related(
            'beneficiary', 'service_provider', 'referring_provider',
            'requested_by', 'reviewed_by', 'approved_by'
        ).prefetch_related('items__service'),
        id=request_id
    )
    
    context = {
        'service_request': service_request,
        'request_items': service_request.items.all(),
        'related_claims': service_request.claims.all(),
    }
    
    return render(request, 'pages/core/services/requests/detail.html', context)


@login_required
def service_request_create(request):
    """Create a new service request"""
    if request.method == 'POST':
        # Handle service request creation logic here
        pass
    
    context = {
        'title': 'Create New Service Request',
    }
    
    return render(request, 'pages/core/services/requests/form.html', context)


@login_required
def service_request_edit(request, request_id):
    """Edit an existing service request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    if request.method == 'POST':
        # Handle service request update logic here
        pass
    
    context = {
        'service_request': service_request,
        'title': f'Edit Service Request {service_request.request_number}',
    }
    
    return render(request, 'pages/core/services/requests/form.html', context)


@login_required
@require_http_methods(["POST"])
def service_request_approve(request, request_id):
    """Approve a service request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    if service_request.status not in ['P', 'U']:
        messages.error(request, 'Service request cannot be approved in its current status.')
        return redirect('service_request_detail', request_id=request_id)
    
    # Update status and approval details
    service_request.status = 'A'
    service_request.approved_by = request.user
    service_request.approval_date = timezone.now()
    service_request.save()
    
    messages.success(request, f'Service request {service_request.request_number} has been approved.')
    return redirect('service_request_detail', request_id=request_id)


@login_required
@require_http_methods(["POST"])
def service_request_decline(request, request_id):
    """Decline a service request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    decline_reason = request.POST.get('decline_reason', '')
    
    if service_request.status not in ['P', 'U']:
        messages.error(request, 'Service request cannot be declined in its current status.')
        return redirect('service_request_detail', request_id=request_id)
    
    # Update status and decline details
    service_request.status = 'D'
    service_request.reviewed_by = request.user
    service_request.review_date = timezone.now()
    service_request.decline_reason = decline_reason
    service_request.save()
    
    messages.success(request, f'Service request {service_request.request_number} has been declined.')
    return redirect('service_request_detail', request_id=request_id)


# Service Views
@login_required
def service_list(request):
    """List all services with filtering and pagination"""
    services = Service.objects.select_related('service_provider_type').prefetch_related('tier_prices')
    
    # Filtering
    provider_type = request.GET.get('provider_type')
    is_active = request.GET.get('is_active')
    requires_auth = request.GET.get('requires_auth')
    search = request.GET.get('search')
    
    if provider_type:
        services = services.filter(service_provider_type_id=provider_type)
    if is_active:
        services = services.filter(is_active=is_active == 'true')
    if requires_auth:
        services = services.filter(requires_authorization=requires_auth == 'true')
    if search:
        services = services.filter(
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(services, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_services': services.count(),
        'active_services': services.filter(is_active=True).count(),
        'auth_required': services.filter(requires_authorization=True).count(),
        'emergency_services': services.filter(is_emergency_service=True).count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'current_filters': {
            'provider_type': provider_type,
            'is_active': is_active,
            'requires_auth': requires_auth,
            'search': search,
        }
    }
    
    return render(request, 'pages/core/services/services/list.html', context)


@login_required
def service_detail(request, service_id):
    """View service details"""
    service = get_object_or_404(
        Service.objects.select_related('service_provider_type').prefetch_related('tier_prices__tier'),
        id=service_id
    )
    
    context = {
        'service': service,
        'tier_prices': service.tier_prices.all(),
    }
    
    return render(request, 'pages/core/services/services/detail.html', context)


@login_required
def service_create(request):
    """Create a new service"""
    if request.method == 'POST':
        # Handle service creation logic here
        pass
    
    context = {
        'title': 'Create New Service',
    }
    
    return render(request, 'pages/core/services/services/form.html', context)


@login_required
def service_edit(request, service_id):
    """Edit an existing service"""
    service = get_object_or_404(Service, id=service_id)
    
    if request.method == 'POST':
        # Handle service update logic here
        pass
    
    context = {
        'service': service,
        'title': f'Edit Service {service.code}',
    }
    
    return render(request, 'pages/core/services/services/form.html', context)


# Adjudication Code Views
@login_required
def adjudication_code_list(request):
    """List all adjudication message codes"""
    codes = AdjudicationMessageCode.objects.all()
    
    # Filtering
    message_type = request.GET.get('message_type')
    category = request.GET.get('category')
    search = request.GET.get('search')
    
    if message_type:
        codes = codes.filter(message_type=message_type)
    if category:
        codes = codes.filter(code__startswith=category)
    if search:
        codes = codes.filter(
            Q(code__icontains=search) |
            Q(short_description__icontains=search) |
            Q(long_description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(codes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_codes': codes.count(),
        'error_codes': codes.filter(message_type='ERROR').count(),
        'warning_codes': codes.filter(message_type='WARNING').count(),
        'info_codes': codes.filter(message_type='INFO').count(),
        'approval_codes': codes.filter(message_type='APPROVAL').count(),
        'decline_codes': codes.filter(message_type='DECLINE').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'message_type_choices': AdjudicationMessageCode.MESSAGE_TYPE_CHOICES,
        'current_filters': {
            'message_type': message_type,
            'category': category,
            'search': search,
        }
    }
    
    return render(request, 'pages/core/services/adjudication/list.html', context)


@login_required
def adjudication_code_detail(request, code_id):
    """View adjudication code details"""
    code = get_object_or_404(AdjudicationMessageCode, id=code_id)
    
    context = {
        'code': code,
    }
    
    return render(request, 'pages/core/services/adjudication/detail.html', context)


# API Views for AJAX requests
@login_required
def api_service_search(request):
    """API endpoint for service search (for autocomplete)"""
    query = request.GET.get('q', '')
    services = Service.objects.filter(
        Q(code__icontains=query) | Q(description__icontains=query),
        is_active=True
    )[:10]
    
    results = [
        {
            'id': service.id,
            'code': service.code,
            'description': service.description,
            'base_price': str(service.base_price),
        }
        for service in services
    ]
    
    return JsonResponse({'results': results})


@login_required
def api_claim_stats(request):
    """API endpoint for claim statistics"""
    # Get date range from request
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    claims = Claim.objects.filter(created_at__date__range=[start_date, end_date])
    
    stats = {
        'total_claims': claims.count(),
        'total_amount': float(claims.aggregate(Sum('claimed_amount'))['claimed_amount__sum'] or 0),
        'approved_amount': float(claims.filter(status='A').aggregate(Sum('adjudicated_amount'))['adjudicated_amount__sum'] or 0),
        'by_status': {
            status[1]: claims.filter(status=status[0]).count()
            for status in Claim.STATUS_CHOICES
        },
        'daily_counts': list(claims.extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(count=Count('id')).order_by('day'))
    }
    
    return JsonResponse(stats)


# Dashboard Views
@login_required
def services_dashboard(request):
    """Services module dashboard"""
    # Recent claims
    recent_claims = Claim.objects.select_related(
        'beneficiary', 'provider'
    ).order_by('-created_at')[:10]
    
    # Pending service requests
    pending_requests = ServiceRequest.objects.filter(
        status__in=['P', 'U']
    ).select_related('beneficiary', 'service_provider').order_by('-requested_date')[:10]
    
    # Statistics for the last 30 days
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    
    stats = {
        'claims': {
            'total': Claim.objects.count(),
            'recent': Claim.objects.filter(created_at__date__gte=thirty_days_ago).count(),
            'pending': Claim.objects.filter(status='N').count(),
            'total_amount': Claim.objects.aggregate(Sum('claimed_amount'))['claimed_amount__sum'] or 0,
        },
        'requests': {
            'total': ServiceRequest.objects.count(),
            'pending': ServiceRequest.objects.filter(status__in=['P', 'U']).count(),
            'approved': ServiceRequest.objects.filter(status='A').count(),
            'recent': ServiceRequest.objects.filter(requested_date__gte=thirty_days_ago).count(),
        },
        'services': {
            'total': Service.objects.count(),
            'active': Service.objects.filter(is_active=True).count(),
            'auth_required': Service.objects.filter(requires_authorization=True).count(),
        }
    }
    
    context = {
        'recent_claims': recent_claims,
        'pending_requests': pending_requests,
        'stats': stats,
    }
    
    return render(request, 'pages/core/services/dashboard.html', context)
