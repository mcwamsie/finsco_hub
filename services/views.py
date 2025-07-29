import csv
import io
import pandas as pd
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta

from .models.claim import Claim, ClaimServiceLine
from .models.service_request import ServiceRequest, ServiceRequestItem
from .models.adjudication import AdjudicationMessageCode
from configurations.models.service import Service, ServiceModifier, ServiceTierPrice
from configurations.models.service_provider import ServiceProvider
from membership.models import Beneficiary
from fisco_hub_8d import settings
from .forms import ClaimForm, ServiceRequestForm, ServiceForm
from configurations.utils.notification_utils import NotificationMixin, htmx_success_response, htmx_error_response
import json


class DashboardView(LoginRequiredMixin, NotificationMixin, TemplateView):
    """Main services dashboard template view that triggers HTMX events"""
    template_name = 'pages/core/services/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics for the last 30 days
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        
        context.update({
            'total_claims': Claim.objects.count(),
            'pending_claims': Claim.objects.filter(status='N').count(),
            'approved_claims': Claim.objects.filter(status='A').count(),
            'total_service_requests': ServiceRequest.objects.count(),
            'pending_service_requests': ServiceRequest.objects.filter(status__in=['P', 'U']).count(),
            'approved_service_requests': ServiceRequest.objects.filter(status='A').count(),
            'total_services': Service.objects.count(),
            'active_services': Service.objects.filter(is_active=True).count(),
            'total_claimed_amount': Claim.objects.aggregate(Sum('claimed_amount'))['claimed_amount__sum'] or 0,
            'total_adjudicated_amount': Claim.objects.aggregate(Sum('adjudicated_amount'))['adjudicated_amount__sum'] or 0,
        })
        return context


# Claim Views
class ClaimTemplateView(LoginRequiredMixin, NotificationMixin, TemplateView):
    template_name = 'pages/core/services/claims/list.html'


class ClaimListView(LoginRequiredMixin, NotificationMixin, ListView):
    """HTMX-powered claim list view"""
    model = Claim
    template_name = 'pages/core/services/partials/claim-list/datatable.html'
    context_object_name = 'claims'
    paginate_by = settings.PAGINATE_BY
    
    def get_queryset(self):
        queryset = Claim.objects.select_related(
            'beneficiary', 'provider', 'service_request', 'user'
        ).prefetch_related('services')
        
        # Search functionality
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(transaction_number__icontains=search) |
                Q(invoice_number__icontains=search) |
                Q(beneficiary__first_name__icontains=search) |
                Q(beneficiary__last_name__icontains=search) |
                Q(provider__name__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filter by provider
        provider = self.request.GET.get('provider', '')
        if provider:
            queryset = queryset.filter(provider_id=provider)
            
        # Filter by beneficiary
        beneficiary = self.request.GET.get('beneficiary', '')
        if beneficiary:
            queryset = queryset.filter(beneficiary_id=beneficiary)
            
        # Filter by date range
        date_from = self.request.GET.get('date_from', '')
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
            
        date_to = self.request.GET.get('date_to', '')
        if date_to:
            queryset = queryset.filter(end_date__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search': self.request.GET.get('search', ''),
            'status_filter': self.request.GET.get('status', ''),
            'provider_filter': self.request.GET.get('provider', ''),
            'beneficiary_filter': self.request.GET.get('beneficiary', ''),
            'date_from_filter': self.request.GET.get('date_from', ''),
            'date_to_filter': self.request.GET.get('date_to', ''),
            'status_choices': Claim.STATUS_CHOICES,
        })
        return context


class ClaimDetailView(LoginRequiredMixin, NotificationMixin, DetailView):
    """Detailed claim view with related data"""
    model = Claim
    template_name = 'pages/core/services/claims/details.html'
    context_object_name = 'claim'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        claim = self.get_object()
        
        # Get related data
        context.update({
            'service_lines': claim.services.all(),
            'adjudication_results': claim.adjudication_results.all() if hasattr(claim, 'adjudication_results') else None,
        })
        
        return context


class ClaimCreateView(LoginRequiredMixin, NotificationMixin, CreateView):
    """Create new claim view (rendered in modal)"""
    model = Claim
    template_name = 'pages/core/services/partials/claim-list/form.html'
    form_class = ClaimForm
    
    def get_success_url(self):
        return reverse_lazy('services:claims_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle successful form submission with HTMX response"""
        claim = form.save(commit=False)
        claim.user = self.request.user
        claim.save()
        self.object = claim

        self.success_notification(self.request, f"Claim '{self.object.transaction_number}' created successfully!")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = self.get_success_url()
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors"""
        if self.request.headers.get('HX-Request'):
            content = render(self.request, self.template_name, {'form': form})
            return htmx_error_response("Please correct the errors below.", content=content)
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modal_title'] = 'Create New Claim'
        context['submit_text'] = 'Create Claim'
        return context


class ClaimUpdateView(LoginRequiredMixin, NotificationMixin, UpdateView):
    """Update claim view (rendered in modal)"""
    model = Claim
    template_name = 'pages/core/services/partials/claim-list/form.html'
    form_class = ClaimForm
    
    def get_success_url(self):
        return reverse_lazy('services:claims_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        self.object = form.save()
        """Handle successful form submission with HTMX response"""
        self.success_notification(self.request, f"Claim '{self.object.transaction_number}' updated successfully!")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = self.get_success_url()
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors"""
        if self.request.headers.get('HX-Request'):
            return htmx_error_response("Please correct the errors below.")
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modal_title'] = f'Update Claim: {self.object.transaction_number}'
        context['submit_text'] = 'Update Claim'
        return context


# Service Request Views
class ServiceRequestTemplateView(LoginRequiredMixin, NotificationMixin, TemplateView):
    """Template view for service requests list page"""
    template_name = 'pages/core/services/requests/list.html'


class ServiceRequestListView(LoginRequiredMixin, NotificationMixin, ListView):
    """List view for service requests"""
    model = ServiceRequest
    template_name = 'pages/core/services/partials/request-list/datatable.html'
    context_object_name = 'service_requests'
    paginate_by = settings.PAGINATE_BY
    
    def get_queryset(self):
        queryset = ServiceRequest.objects.select_related(
            'beneficiary', 'service_provider', 'referring_provider', 
            'requested_by', 'reviewed_by', 'approved_by'
        ).prefetch_related('items__service')
        
        # Search functionality
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(request_number__icontains=search) |
                Q(beneficiary__first_name__icontains=search) |
                Q(beneficiary__last_name__icontains=search) |
                Q(service_provider__name__icontains=search) |
                Q(chief_complaint__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filter by priority
        priority = self.request.GET.get('priority', '')
        if priority:
            queryset = queryset.filter(priority=priority)
            
        # Filter by provider
        provider = self.request.GET.get('provider', '')
        if provider:
            queryset = queryset.filter(service_provider_id=provider)
            
        # Filter by beneficiary
        beneficiary = self.request.GET.get('beneficiary', '')
        if beneficiary:
            queryset = queryset.filter(beneficiary_id=beneficiary)
            
        # Filter by date range
        date_from = self.request.GET.get('date_from', '')
        if date_from:
            queryset = queryset.filter(requested_date__gte=date_from)
            
        date_to = self.request.GET.get('date_to', '')
        if date_to:
            queryset = queryset.filter(requested_date__lte=date_to)
        
        return queryset.order_by('-requested_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search': self.request.GET.get('search', ''),
            'status_filter': self.request.GET.get('status', ''),
            'priority_filter': self.request.GET.get('priority', ''),
            'provider_filter': self.request.GET.get('provider', ''),
            'beneficiary_filter': self.request.GET.get('beneficiary', ''),
            'date_from_filter': self.request.GET.get('date_from', ''),
            'date_to_filter': self.request.GET.get('date_to', ''),
            'status_choices': ServiceRequest.STATUS_CHOICES,
            'priority_choices': ServiceRequest.PRIORITY_CHOICES,
        })
        return context


class ServiceRequestDetailView(LoginRequiredMixin, NotificationMixin, DetailView):
    """Detail view for a specific service request"""
    model = ServiceRequest
    template_name = 'pages/core/services/requests/details.html'
    context_object_name = 'service_request'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add related data
        context['request_items'] = self.object.items.all()
        context['related_claims'] = self.object.claims.all()
        
        return context


class ServiceRequestCreateView(LoginRequiredMixin, NotificationMixin, CreateView):
    """Create new service request view (rendered in modal)"""
    model = ServiceRequest
    template_name = 'pages/core/services/partials/request-list/form.html'
    form_class = ServiceRequestForm
    
    def get_success_url(self):
        return reverse_lazy('services:requests_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle successful form submission with HTMX response"""
        service_request = form.save(commit=False)
        service_request.requested_by = self.request.user
        service_request.save()
        self.object = service_request

        self.success_notification(self.request, f"Service Request '{self.object.request_number}' created successfully!")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = self.get_success_url()
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors"""
        if self.request.headers.get('HX-Request'):
            content = render(self.request, self.template_name, {'form': form})
            return htmx_error_response("Please correct the errors below.", content=content)
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modal_title'] = 'Create New Service Request'
        context['submit_text'] = 'Create Service Request'
        return context


class ServiceRequestUpdateView(LoginRequiredMixin, NotificationMixin, UpdateView):
    """Update service request view (rendered in modal)"""
    model = ServiceRequest
    template_name = 'pages/core/services/partials/request-list/form.html'
    form_class = ServiceRequestForm
    
    def get_success_url(self):
        return reverse_lazy('services:requests_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        self.object = form.save()
        """Handle successful form submission with HTMX response"""
        self.success_notification(self.request, f"Service Request '{self.object.request_number}' updated successfully!")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = self.get_success_url()
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors"""
        if self.request.headers.get('HX-Request'):
            return htmx_error_response("Please correct the errors below.")
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modal_title'] = f'Update Service Request: {self.object.request_number}'
        context['submit_text'] = 'Update Service Request'
        return context


# Service Views
class ServiceTemplateView(LoginRequiredMixin, NotificationMixin, TemplateView):
    """Template view for services list page"""
    template_name = 'pages/core/services/services/list.html'


class ServiceListView(LoginRequiredMixin, NotificationMixin, ListView):
    """List view for services"""
    model = Service
    template_name = 'pages/core/services/partials/services-list/datatable.html'
    context_object_name = 'services'
    paginate_by = settings.PAGINATE_BY
    
    def get_queryset(self):
        queryset = Service.objects.select_related('service_provider_type').prefetch_related('tier_prices')
        
        # Search functionality
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Filter by provider type
        provider_type = self.request.GET.get('provider_type', '')
        if provider_type:
            queryset = queryset.filter(service_provider_type_id=provider_type)
            
        # Filter by active status
        is_active = self.request.GET.get('is_active', '')
        if is_active:
            queryset = queryset.filter(is_active=is_active == 'true')
            
        # Filter by authorization requirement
        requires_auth = self.request.GET.get('requires_auth', '')
        if requires_auth:
            queryset = queryset.filter(requires_authorization=requires_auth == 'true')
        
        return queryset.order_by('code')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search': self.request.GET.get('search', ''),
            'provider_type_filter': self.request.GET.get('provider_type', ''),
            'is_active_filter': self.request.GET.get('is_active', ''),
            'requires_auth_filter': self.request.GET.get('requires_auth', ''),
        })
        return context


class ServiceDetailView(LoginRequiredMixin, NotificationMixin, DetailView):
    """Detail view for a specific service"""
    model = Service
    template_name = 'pages/core/services/services/details.html'
    context_object_name = 'service'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add related data
        context['tier_prices'] = self.object.tier_prices.all()
        
        return context


class ServiceCreateView(LoginRequiredMixin, NotificationMixin, CreateView):
    """Create new service view (rendered in modal)"""
    model = Service
    template_name = 'pages/core/services/partials/services-list/form.html'
    form_class = ServiceForm
    
    def get_success_url(self):
        return reverse_lazy('services:services_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle successful form submission with HTMX response"""
        self.object = form.save()
        self.success_notification(self.request, f"Service '{self.object.code}' created successfully!")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = self.get_success_url()
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors"""
        if self.request.headers.get('HX-Request'):
            content = render(self.request, self.template_name, {'form': form})
            return htmx_error_response("Please correct the errors below.", content=content)
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modal_title'] = 'Create New Service'
        context['submit_text'] = 'Create Service'
        return context


class ServiceUpdateView(LoginRequiredMixin, NotificationMixin, UpdateView):
    """Update service view (rendered in modal)"""
    model = Service
    template_name = 'pages/core/services/partials/services-list/form.html'
    form_class = ServiceForm
    
    def get_success_url(self):
        return reverse_lazy('services:services_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        self.object = form.save()
        """Handle successful form submission with HTMX response"""
        self.success_notification(self.request, f"Service '{self.object.code}' updated successfully!")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = self.get_success_url()
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors"""
        if self.request.headers.get('HX-Request'):
            return htmx_error_response("Please correct the errors below.")
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modal_title'] = f'Update Service: {self.object.code}'
        context['submit_text'] = 'Update Service'
        return context


# Additional utility views for HTMX interactions

def claim_search_suggestions(request):
    """HTMX endpoint for claim search suggestions"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    claims = Claim.objects.filter(
        Q(transaction_number__icontains=query) | 
        Q(invoice_number__icontains=query) |
        Q(beneficiary__first_name__icontains=query) |
        Q(beneficiary__last_name__icontains=query)
    ).select_related('beneficiary', 'provider')[:10]
    
    suggestions = [
        {
            'id': claim.id,
            'transaction_number': claim.transaction_number,
            'invoice_number': claim.invoice_number,
            'beneficiary_name': f"{claim.beneficiary.first_name} {claim.beneficiary.last_name}",
            'provider_name': claim.provider.name,
            'claimed_amount': str(claim.claimed_amount)
        }
        for claim in claims
    ]
    
    return JsonResponse({'suggestions': suggestions})


def claim_quick_stats(request):
    """HTMX endpoint for claim quick statistics"""
    stats = {
        'total_claims': Claim.objects.count(),
        'new_claims': Claim.objects.filter(status='N').count(),
        'approved_claims': Claim.objects.filter(status='A').count(),
        'rejected_claims': Claim.objects.filter(status='D').count(),
    }
    
    return render(request, 'pages/core/services/partials/claim-list/_quick_stats.html', {'stats': stats})


def toggle_claim_status(request, claim_id):
    """HTMX endpoint to toggle claim status"""
    if request.method != 'POST':
        return htmx_error_response("Invalid request method.")
    
    try:
        claim = get_object_or_404(Claim, id=claim_id)
        
        # Toggle status logic (simplified)
        if claim.status == 'N':
            claim.status = 'U'
            status_text = 'moved to under review'
        elif claim.status == 'U':
            claim.status = 'A'
            status_text = 'approved'
        else:
            return htmx_error_response("Cannot change status of this claim.")
        
        claim.save()
        
        return htmx_success_response(
            f"Claim '{claim.transaction_number}' has been {status_text}.",
            f'<script>htmx.trigger("#claim-list", "refresh");</script>'
        )
        
    except Exception as e:
        return htmx_error_response(f"Error updating claim status: {str(e)}")


def service_request_search_suggestions(request):
    """HTMX endpoint for service request search suggestions"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    requests = ServiceRequest.objects.filter(
        Q(request_number__icontains=query) | 
        Q(beneficiary__first_name__icontains=query) |
        Q(beneficiary__last_name__icontains=query) |
        Q(chief_complaint__icontains=query)
    ).select_related('beneficiary', 'service_provider')[:10]
    
    suggestions = [
        {
            'id': request.id,
            'request_number': request.request_number,
            'beneficiary_name': f"{request.beneficiary.first_name} {request.beneficiary.last_name}",
            'provider_name': request.service_provider.name,
            'status': request.get_status_display()
        }
        for request in requests
    ]
    
    return JsonResponse({'suggestions': suggestions})


def service_request_quick_stats(request):
    """HTMX endpoint for service request quick statistics"""
    stats = {
        'total_requests': ServiceRequest.objects.count(),
        'pending_requests': ServiceRequest.objects.filter(status='P').count(),
        'approved_requests': ServiceRequest.objects.filter(status='A').count(),
        'declined_requests': ServiceRequest.objects.filter(status='D').count(),
    }
    
    return render(request, 'pages/core/services/partials/request-list/_quick_stats.html', {'stats': stats})


def toggle_service_request_status(request, request_id):
    """HTMX endpoint to toggle service request status"""
    if request.method != 'POST':
        return htmx_error_response("Invalid request method.")
    
    try:
        service_request = get_object_or_404(ServiceRequest, id=request_id)
        
        # Toggle status logic (simplified)
        if service_request.status == 'P':
            service_request.status = 'A'
            service_request.approved_by = request.user
            service_request.approval_date = timezone.now()
            status_text = 'approved'
        elif service_request.status == 'A':
            service_request.status = 'D'
            service_request.reviewed_by = request.user
            service_request.review_date = timezone.now()
            status_text = 'declined'
        else:
            return htmx_error_response("Cannot change status of this service request.")
        
        service_request.save()
        
        return htmx_success_response(
            f"Service Request '{service_request.request_number}' has been {status_text}.",
            f'<script>htmx.trigger("#service-request-list", "refresh");</script>'
        )
        
    except Exception as e:
        return htmx_error_response(f"Error updating service request status: {str(e)}")


def service_search_suggestions(request):
    """HTMX endpoint for service search suggestions"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    services = Service.objects.filter(
        Q(code__icontains=query) | 
        Q(description__icontains=query),
        is_active=True
    )[:10]
    
    suggestions = [
        {
            'id': service.id,
            'code': service.code,
            'description': service.description,
            'base_price': str(service.base_price),
            'requires_auth': service.requires_authorization
        }
        for service in services
    ]
    
    return JsonResponse({'suggestions': suggestions})


def service_quick_stats(request):
    """HTMX endpoint for service quick statistics"""
    stats = {
        'total_services': Service.objects.count(),
        'active_services': Service.objects.filter(is_active=True).count(),
        'inactive_services': Service.objects.filter(is_active=False).count(),
        'auth_required_services': Service.objects.filter(requires_authorization=True).count(),
    }
    
    return render(request, 'pages/core/services/partials/services-list/_quick_stats.html', {'stats': stats})


def toggle_service_status(request, service_id):
    """HTMX endpoint to toggle service status"""
    if request.method != 'POST':
        return htmx_error_response("Invalid request method.")
    
    try:
        service = get_object_or_404(Service, id=service_id)
        
        # Toggle status
        if service.is_active:
            service.is_active = False
            status_text = 'deactivated'
        else:
            service.is_active = True
            status_text = 'activated'
        
        service.save()
        
        return htmx_success_response(
            f"Service '{service.code}' has been {status_text}.",
            f'<script>htmx.trigger("#service-list", "refresh");</script>'
        )
        
    except Exception as e:
        return htmx_error_response(f"Error updating service status: {str(e)}")


# Lookup endpoints for HTMX
def beneficiary_lookup(request):
    """HTMX endpoint for beneficiary lookup"""
    query = request.GET.get('q', '')
    beneficiaries = Beneficiary.objects.filter(
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query) |
        Q(membership_number__icontains=query),
        status='A'
    )[:10]
    
    results = [
        {
            'id': beneficiary.id,
            'name': f"{beneficiary.first_name} {beneficiary.last_name}",
            'membership_number': beneficiary.membership_number,
            'member_name': beneficiary.member.name
        }
        for beneficiary in beneficiaries
    ]
    
    return JsonResponse({'results': results})


def service_provider_lookup(request):
    """HTMX endpoint for service provider lookup"""
    query = request.GET.get('q', '')
    providers = ServiceProvider.objects.filter(
        Q(name__icontains=query) | 
        Q(identification_no__icontains=query),
        status='A'
    )[:10]
    
    results = [
        {
            'id': provider.id,
            'name': provider.name,
            'identification_no': provider.identification_no,
            'type': provider.service_provider_type.name if provider.service_provider_type else ''
        }
        for provider in providers
    ]
    
    return JsonResponse({'results': results})


def service_lookup(request):
    """HTMX endpoint for service lookup"""
    query = request.GET.get('q', '')
    services = Service.objects.filter(
        Q(code__icontains=query) | 
        Q(description__icontains=query),
        is_active=True
    )[:10]
    
    results = [
        {
            'id': service.id,
            'code': service.code,
            'description': service.description,
            'base_price': str(service.base_price)
        }
        for service in services
    ]
    
    return JsonResponse({'results': results})


# Adjudication endpoints
def adjudicate_claim(request, claim_id):
    """HTMX endpoint for claim adjudication"""
    if request.method != 'POST':
        return htmx_error_response("Invalid request method.")
    
    try:
        claim = get_object_or_404(Claim, id=claim_id)
        
        # Simple adjudication logic (you can expand this)
        if claim.status == 'N' or claim.status == 'U':
            claim.status = 'A'
            claim.adjudicated_amount = claim.claimed_amount  # Simplified
            claim.save()
            
            return htmx_success_response(
                f"Claim '{claim.transaction_number}' has been adjudicated and approved.",
                f'<script>htmx.trigger("#claim-list", "refresh");</script>'
            )
        else:
            return htmx_error_response("Claim cannot be adjudicated in its current status.")
        
    except Exception as e:
        return htmx_error_response(f"Error adjudicating claim: {str(e)}")


def approve_service_request(request, request_id):
    """HTMX endpoint for service request approval"""
    if request.method != 'POST':
        return htmx_error_response("Invalid request method.")
    
    try:
        service_request = get_object_or_404(ServiceRequest, id=request_id)
        
        if service_request.status in ['P', 'U']:
            service_request.status = 'A'
            service_request.approved_by = request.user
            service_request.approval_date = timezone.now()
            service_request.approved_amount = service_request.estimated_amount  # Simplified
            service_request.save()
            
            return htmx_success_response(
                f"Service Request '{service_request.request_number}' has been approved.",
                f'<script>htmx.trigger("#service-request-list", "refresh");</script>'
            )
        else:
            return htmx_error_response("Service request cannot be approved in its current status.")
        
    except Exception as e:
        return htmx_error_response(f"Error approving service request: {str(e)}")


def decline_service_request(request, request_id):
    """HTMX endpoint for service request declination"""
    if request.method != 'POST':
        return htmx_error_response("Invalid request method.")
    
    try:
        service_request = get_object_or_404(ServiceRequest, id=request_id)
        decline_reason = request.POST.get('decline_reason', '')
        
        if service_request.status in ['P', 'U']:
            service_request.status = 'D'
            service_request.reviewed_by = request.user
            service_request.review_date = timezone.now()
            service_request.decline_reason = decline_reason
            service_request.save()
            
            return htmx_success_response(
                f"Service Request '{service_request.request_number}' has been declined.",
                f'<script>htmx.trigger("#service-request-list", "refresh");</script>'
            )
        else:
            return htmx_error_response("Service request cannot be declined in its current status.")
        
    except Exception as e:
        return htmx_error_response(f"Error declining service request: {str(e)}")
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


# Import/Export Views

@require_http_methods(["GET"])
def claims_import(request):
    """HTMX endpoint for claim import modal"""
    return render(request, 'components/modals/import-modal.html', {
        'modal_title': 'Import Claims',
        'import_url': reverse_lazy('services:claims_import_process'),
        'sample_url': reverse_lazy('services:claims_sample_template'),
        'entity_name': 'claims'
    })


@require_http_methods(["GET"])
def claims_export(request):
    """HTMX endpoint for claim export modal"""
    return render(request, 'components/modals/export-modal.html', {
        'modal_title': 'Export Claims',
        'export_url': reverse_lazy('services:claims_export_process'),
        'entity_name': 'claims'
    })


@require_http_methods(["POST"])
@csrf_exempt
def claims_import_process(request):
    """Process claim import from uploaded file"""
    from configurations.utils.import_tracker import ImportResultTracker
    
    tracker = None
    import_result = None
    try:
        from configurations.forms import ClaimImportForm
        from .admin import ClaimResource
        from import_export import base_formats
        
        # Initialize form with proper formats and resources
        form = ClaimImportForm(
            request.POST, 
            request.FILES,
            formats=base_formats.DEFAULT_FORMATS,
            resources=[ClaimResource]
        )
        
        if not form.is_valid():
            return JsonResponse({
                'success': False, 
                'error': 'Form validation failed',
                'errors': form.errors
            })
        
        # Get form data
        import_file = form.cleaned_data['import_file']
        validate_only = form.cleaned_data.get('validate_only', False)
        skip_duplicates = form.cleaned_data.get('skip_duplicates', False)
        validate_transaction_numbers = form.cleaned_data.get('validate_transaction_numbers', False)
        auto_generate_missing = form.cleaned_data.get('auto_generate_missing', False)
        validate_beneficiary_numbers = form.cleaned_data.get('validate_beneficiary_numbers', False)
        validate_provider_numbers = form.cleaned_data.get('validate_provider_numbers', False)
        
        # Start tracking the import
        tracker = ImportResultTracker()
        import_result = tracker.start_import(
            import_type='claim',
            user=request.user,
            original_filename=import_file.name,
            file_size=import_file.size
        )
        
        # Initialize resource
        resource = ClaimResource()
        
        # Determine file format
        if import_file.name.endswith('.xlsx'):
            format_type = base_formats.XLSX()
        elif import_file.name.endswith('.xls'):
            format_type = base_formats.XLS()
        else:
            format_type = base_formats.CSV()
        
        # Read the uploaded file and create dataset
        imported_data = format_type.create_dataset(import_file.read())
        
        # Perform dry run
        result = resource.import_data(imported_data, dry_run=True)
        
        if result.has_errors():
            errors = []
            for row_errors in result.row_errors():
                errors.append(f"Row {row_errors[0]}: {', '.join([str(e.error) for e in row_errors[1]])}")
            
            # Track the failure
            tracker.fail_import(import_result, f"Validation failed: {'; '.join(errors[:3])}")
            
            return JsonResponse({
                'success': False,
                'error': 'Import validation failed',
                'errors': errors[:10],  # Limit to first 10 errors
                'import_result_id': import_result.id
            })
        
        # If validation only, return results
        if validate_only:
            tracker.complete_import(import_result, "Validation completed successfully")
            
            from django.urls import reverse
            results_url = reverse('configurations:import_result_detail', args=[import_result.id])
            
            return JsonResponse({
                'success': True,
                'message': f'Validation complete. {len(result.rows)} records would be processed.',
                'total_rows': len(result.rows),
                'new_records': len([r for r in result.rows if r.import_type == 'new']),
                'updated_records': len([r for r in result.rows if r.import_type == 'update']),
                'skipped_records': len([r for r in result.rows if r.import_type == 'skip']),
                'import_result_id': import_result.id,
                'results_url': results_url
            })
        
        # Perform actual import
        result = resource.import_data(imported_data, dry_run=False)
        
        if result.has_errors():
            errors = []
            for row_errors in result.row_errors():
                errors.append(f"Row {row_errors[0]}: {', '.join([str(e.error) for e in row_errors[1]])}")
            
            # Track the failure
            tracker.fail_import(import_result, f"Import failed: {'; '.join(errors[:3])}")
            
            return JsonResponse({
                'success': False,
                'error': 'Import failed',
                'errors': errors[:10],
                'import_result_id': import_result.id
            })
        
        # Process the import result and track it
        tracker.process_import_export_result(import_result, result, imported_data)
        tracker.complete_import(import_result)
        
        from django.urls import reverse
        results_url = reverse('configurations:import_result_detail', args=[import_result.id])
        
        return JsonResponse({
            'success': True,
            'message': f'Import complete! Processed {len(result.rows)} records.',
            'total_rows': len(result.rows),
            'new_records': len([r for r in result.rows if r.import_type == 'new']),
            'updated_records': len([r for r in result.rows if r.import_type == 'update']),
            'skipped_records': len([r for r in result.rows if r.import_type == 'skip']),
            'import_result_id': import_result.id,
            'results_url': results_url
        })
        
    except Exception as e:
        if tracker and import_result:
            tracker.fail_import(import_result, str(e))
        return JsonResponse({
            'success': False, 
            'error': str(e),
            'import_result_id': import_result.id if import_result else None
        })


@require_http_methods(["POST"])
def claims_export_process(request):
    """Process claim export to file"""
    try:
        from .admin import ClaimResource
        from import_export import base_formats
        
        export_format = request.POST.get('export_format', 'csv')
        include_inactive = request.POST.get('include_inactive') == 'on'
        include_related = request.POST.get('include_related') == 'on'
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        
        # Build queryset
        queryset = Claim.objects.select_related('beneficiary', 'provider', 'user')
        
        if not include_inactive:
            queryset = queryset.exclude(status='C')  # Exclude cancelled claims
        
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        # Initialize resource and export data
        resource = ClaimResource()
        dataset = resource.export(queryset)
        
        # Determine format
        if export_format == 'excel':
            format_type = base_formats.XLSX()
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            file_extension = 'xlsx'
        else:
            format_type = base_formats.CSV()
            content_type = 'text/csv'
            file_extension = 'csv'
        
        # Generate filename
        filename = f"claims_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        
        # Create response
        response = HttpResponse(
            format_type.export_data(dataset),
            content_type=content_type
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def claims_sample_template(request):
    """Download sample template for claim import"""
    try:
        from .admin import ClaimResource
        from import_export import base_formats
        
        # Initialize resource
        resource = ClaimResource()
        
        # Create sample data
        sample_data = [
            {
                'transaction_number': 'CLM001',
                'invoice_number': 'INV001',
                'beneficiary': '1',  # Use ID as per ClaimResource
                'provider': '1',     # Use ID as per ClaimResource
                'claimed_amount': '1000.00',
                'adjudicated_amount': '950.00',
                'status': 'N',
                'start_date': '2024-01-01',
                'end_date': '2024-01-01'
            },
            {
                'transaction_number': 'CLM002',
                'invoice_number': 'INV002',
                'beneficiary': '2',
                'provider': '1',
                'claimed_amount': '750.00',
                'adjudicated_amount': '700.00',
                'status': 'A',
                'start_date': '2024-01-02',
                'end_date': '2024-01-02'
            }
        ]
        
        # Create dataset from sample data
        dataset = resource.export()
        dataset.dict = sample_data
        
        # Export as CSV
        format_type = base_formats.CSV()
        
        response = HttpResponse(
            format_type.export_data(dataset),
            content_type='text/csv'
        )
        response['Content-Disposition'] = 'attachment; filename="claims_import_template.csv"'
        
        return response
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
