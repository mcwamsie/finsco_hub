from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone

from configurations.models.member import Member
from fisco_hub_8d import settings
from membership.forms import MemberForm, BeneficiaryForm, TopUpForm
from membership.models import Beneficiary, TopUp, ApplicantMember
from accounting.models.member_account import MemberAccount
from configurations.utils.notification_utils import NotificationMixin, htmx_success_response, htmx_error_response
import json


class DashboardView(LoginRequiredMixin, NotificationMixin, TemplateView):
    """Main membership dashboard template view that triggers HTMX events"""
    template_name = 'pages/core/membership/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'total_members': Member.objects.count(),
            'active_members': Member.objects.filter(status='A').count(),
            'pending_applications': ApplicantMember.objects.filter(status='P').count(),
            'total_beneficiaries': Beneficiary.objects.count(),
            'total_topups': TopUp.objects.count(),
            'pending_topups': TopUp.objects.filter(status='P').count(),
        })
        return context

class MemberTemplateView(LoginRequiredMixin, NotificationMixin, TemplateView):
    template_name = 'pages/core/membership/members/list.html'

class MemberListView(LoginRequiredMixin, NotificationMixin, ListView):
    """HTMX-powered member list view"""
    model = Member
    template_name = 'pages/core/membership/partials/member-list/datatable.html'
    context_object_name = 'members'
    paginate_by = settings.PAGINATE_BY
    
    def get_queryset(self):
        queryset = Member.objects.select_related('currency', 'default_package', 'registered_by')
        
        # Search functionality
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(parent__name__icontains=search) |
                Q(membership_number__icontains=search) |
                Q(email__icontains=search) |
                Q(mobile__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filter by type
        member_type = self.request.GET.get('type', '')
        if member_type:
            queryset = queryset.filter(type=member_type)
            
        # Filter by KYC status
        kyc_status = self.request.GET.get('kyc_status', '')
        if kyc_status == 'verified':
            queryset = queryset.filter(kyc_verified_at__isnull=False)
        elif kyc_status == 'pending':
            queryset = queryset.filter(kyc_verified_at__isnull=True)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search': self.request.GET.get('search', ''),
            'status_filter': self.request.GET.get('status', ''),
            'type_filter': self.request.GET.get('type', ''),
            'kyc_filter': self.request.GET.get('kyc_status', ''),
            'member_types': Member.MEMBER_TYPES,
            'status_choices': [('A', 'Active'), ('I', 'Inactive'), ('S', 'Suspended')],
        })
        return context


class MemberDetailView(LoginRequiredMixin, NotificationMixin, DetailView):
    """Detailed member view with related data"""
    model = Member
    template_name = 'pages/core/membership/members/details.html'
    context_object_name = 'member'
    slug_field = 'membership_number'
    slug_url_kwarg = 'membership_number'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        
        # Get related data
        context.update({
            'beneficiaries': Beneficiary.objects.filter(member=member).order_by('-created_at'),
            'accounts': MemberAccount.objects.filter(member=member).select_related('currency'),
            'recent_topups': TopUp.objects.filter(member=member).order_by('-created_at')[:10],
            'kyc_documents': member.kyc_documents.select_related('requirement').order_by('-created_at'),
            'sub_members': member.sub_members.all() if member.type == 'CO' else None,
        })
        
        return context


class MemberCreateView(LoginRequiredMixin, NotificationMixin, CreateView):
    """Create new member view (rendered in modal)"""
    model = Member
    template_name = 'pages/core/membership/partials/member-list/form.html'
    form_class = MemberForm
    
    def get_success_url(self):
        return reverse_lazy('membership:members_detail', kwargs={'membership_number': self.object.membership_number})
    
    def form_valid(self, form):
        """Handle successful form submission with HTMX response"""

        member = form.save(commit=False)
        # form.registered_by = self.request.user
        member.status = "A"
        member.save()
        self.object = member

        self.success_notification(self.request, f"Member '{self.object.name}' created successfully!")
        response = HttpResponse(status=200)
        response["HX-Redirect"] = self.get_success_url()
        return response
    
    def form_invalid(self, form):
        print(form.errors)
        """Handle form validation errors"""
        if self.request.headers.get('HX-Request'):
            content = render(self.request ,self.template_name, {'form': form} )
            return htmx_error_response("Please correct the errors below.", content=content)
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modal_title'] = 'Create New Member'
        context['submit_text'] = 'Create Member'
        return context


class MemberUpdateView(LoginRequiredMixin, NotificationMixin, UpdateView):
    """Update member view (rendered in modal)"""
    model = Member
    template_name = 'pages/core/membership/partials/member-list/form.html'
    form_class = MemberForm
    slug_field = 'membership_number'
    slug_url_kwarg = 'membership_number'
    
    def get_success_url(self):
        return reverse_lazy('membership:members_detail', kwargs={'membership_number': self.object.membership_number})
    
    def form_valid(self, form):
        self.object = form.save()
        """Handle successful form submission with HTMX response"""
        self.success_notification(self.request, f"Member '{self.object.name}' updated successfully!")
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
        context['modal_title'] = f'Update Member: {self.object.name}'
        context['submit_text'] = 'Update Member'
        return context


# Additional utility views for HTMX interactions

def member_search_suggestions(request):
    """HTMX endpoint for member search suggestions"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    members = Member.objects.filter(
        Q(name__icontains=query) | 
        Q(parent__name__icontains=query) |
        Q(membership_number__icontains=query) |
        Q(email__icontains=query)
    )[:10]
    
    suggestions = [
        {
            'id': member.id,
            'name': member.name,
            'membership_number': member.membership_number,
            'email': member.email
        }
        for member in members
    ]
    
    return JsonResponse({'suggestions': suggestions})


def member_quick_stats(request, membership_number):
    """HTMX endpoint for member quick statistics"""
    member = get_object_or_404(Member, membership_number=membership_number)
    
    # Calculate statistics
    total_balance = sum(
        account.balance for account in member.accounts.all()
    )
    
    beneficiaries_count = member.beneficiaries.count() if hasattr(member, 'beneficiaries') else 0
    recent_topups_count = TopUp.objects.filter(member=member).count()
    
    context = {
        'member': member,
        'total_balance': total_balance,
        'beneficiaries_count': beneficiaries_count,
        'recent_topups_count': recent_topups_count,
    }
    
    return render(request, 'pages/core/membership/partials/member_quick_stats.html', context)


def toggle_member_status(request, member_id):
    """HTMX endpoint to toggle member status"""
    if request.method != 'POST':
        return htmx_error_response("Invalid request method.")
    
    try:
        member = get_object_or_404(Member, id=member_id)
        
        # Toggle status
        if member.status == 'A':
            member.status = 'I'
            status_text = 'deactivated'
        else:
            member.status = 'A'
            status_text = 'activated'
        
        member.save()
        
        return htmx_success_response(
            f"Member '{member.name}' has been {status_text}.",
            f'<script>htmx.trigger("#member-list", "refresh");</script>'
        )
        
    except Exception as e:
        return htmx_error_response(f"Error updating member status: {str(e)}")


# Beneficiary views
class BeneficiaryTemplateView(LoginRequiredMixin, NotificationMixin, TemplateView):
    """Template view for beneficiaries list page"""
    template_name = 'pages/core/membership/beneficiaries/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['beneficiary_types'] = Beneficiary.TYPE_CHOICES
        context['status_choices'] = Beneficiary.STATUS_CHOICES
        
        # Add statistics
        context['total_beneficiaries'] = Beneficiary.objects.count()
        context['active_beneficiaries'] = Beneficiary.objects.filter(status='A').count()
        context['principal_count'] = Beneficiary.objects.filter(type='P').count()
        context['dependent_count'] = Beneficiary.objects.filter(type='D').count()
        
        return context


class BeneficiaryListView(LoginRequiredMixin, NotificationMixin, ListView):
    """List view for beneficiaries"""
    model = Beneficiary
    template_name = 'pages/core/membership/partials/beneficiary-list/datatable.html'
    context_object_name = 'beneficiaries'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Beneficiary.objects.select_related('member', 'principal')
        
        # Filter by member if specified
        member_id = self.request.GET.get('member')
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        
        # Filter by type
        beneficiary_type = self.request.GET.get('type', '')
        if beneficiary_type:
            queryset = queryset.filter(type=beneficiary_type)
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search functionality
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(member__name__icontains=search) |
                Q(membership_number__icontains=search) |
                Q(national_id_number__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['beneficiary_types'] = Beneficiary.TYPE_CHOICES
        context['status_choices'] = Beneficiary.STATUS_CHOICES
        
        # Add statistics
        context['total_beneficiaries'] = Beneficiary.objects.count()
        context['active_beneficiaries'] = Beneficiary.objects.filter(status='A').count()
        context['principal_count'] = Beneficiary.objects.filter(type='P').count()
        context['dependent_count'] = Beneficiary.objects.filter(type='D').count()
        
        return context


class BeneficiaryDetailView(LoginRequiredMixin, NotificationMixin, DetailView):
    """Detail view for a specific beneficiary"""
    model = Beneficiary
    template_name = 'pages/core/membership/beneficiaries/details.html'
    context_object_name = 'beneficiary'
    slug_field = 'membership_number'
    slug_url_kwarg = 'membership_number'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add related data
        context['member'] = self.object.member
        context['dependents'] = Beneficiary.objects.filter(principal=self.object)
        
        # Add claims if available
        if hasattr(self.object, 'claims'):
            context['recent_claims'] = self.object.claims.order_by('-created_at')[:5]
        
        return context


class BeneficiaryCreateView(LoginRequiredMixin, NotificationMixin, CreateView):
    """Create new beneficiary view (rendered in modal)"""
    model = Beneficiary
    template_name = 'pages/core/membership/partials/beneficiary-list/form.html'
    form_class = BeneficiaryForm
    
    def get_success_url(self):
        return reverse_lazy('membership:beneficiaries_detail', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        """Handle successful form submission with HTMX response"""
        self.object = form.save()
        self.success_notification(self.request, f"Beneficiary '{self.object.first_name} {self.object.last_name}' created successfully!")
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
        context['modal_title'] = 'Create New Beneficiary'
        context['submit_text'] = 'Create Beneficiary'
        return context


class BeneficiaryUpdateView(LoginRequiredMixin, NotificationMixin, UpdateView):
    """Update beneficiary view (rendered in modal)"""
    model = Beneficiary
    template_name = 'pages/core/membership/partials/beneficiary-list/form.html'
    form_class = BeneficiaryForm
    # slug_field = 'membership_number'
    # slug_url_kwarg = 'membership_number'
    #
    def get_success_url(self):
        return reverse_lazy('membership:beneficiaries_detail', kwargs={'membership_number': self.object.membership_number})
    
    def form_valid(self, form):
        self.object = form.save()
        """Handle successful form submission with HTMX response"""
        self.success_notification(self.request, f"Beneficiary '{self.object.first_name} {self.object.last_name}' updated successfully!")
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
        context['modal_title'] = f'Update Beneficiary: {self.object.first_name} {self.object.last_name}'
        context['submit_text'] = 'Update Beneficiary'
        return context


# Additional utility views for HTMX interactions

def beneficiary_search_suggestions(request):
    """HTMX endpoint for beneficiary search suggestions"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    beneficiaries = Beneficiary.objects.filter(
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query) |
        Q(membership_number__icontains=query) |
        Q(national_id_number__icontains=query) |
        Q(email__icontains=query)
    ).select_related('member')[:10]
    
    suggestions = [
        {
            'id': beneficiary.id,
            'name': f"{beneficiary.first_name} {beneficiary.last_name}",
            'membership_number': beneficiary.membership_number,
            'member_name': beneficiary.member.name,
            'type': beneficiary.get_type_display()
        }
        for beneficiary in beneficiaries
    ]
    
    return JsonResponse({'suggestions': suggestions})


def beneficiary_quick_stats(request, membership_number):
    """HTMX endpoint for beneficiary quick statistics"""
    beneficiary = get_object_or_404(Beneficiary, membership_number=membership_number)
    
    # Calculate statistics
    dependents_count = Beneficiary.objects.filter(principal=beneficiary).count() if beneficiary.type == 'P' else 0
    claims_count = beneficiary.claims.count() if hasattr(beneficiary, 'claims') else 0
    
    context = {
        'beneficiary': beneficiary,
        'dependents_count': dependents_count,
        'claims_count': claims_count,
        'annual_limit': beneficiary.annual_limit,
    }
    
    return render(request, 'pages/core/membership/partials/beneficiary_quick_stats.html', context)


def toggle_beneficiary_status(request, beneficiary_id):
    """HTMX endpoint to toggle beneficiary status"""
    if request.method != 'POST':
        return htmx_error_response("Invalid request method.")
    
    try:
        beneficiary = get_object_or_404(Beneficiary, id=beneficiary_id)
        
        # Toggle status
        if beneficiary.status == 'A':
            beneficiary.status = 'I'
            status_text = 'deactivated'
        else:
            beneficiary.status = 'A'
            status_text = 'activated'
        
        beneficiary.save()
        
        return htmx_success_response(
            f"Beneficiary '{beneficiary.first_name} {beneficiary.last_name}' has been {status_text}.",
            f'<script>htmx.trigger("#beneficiary-list", "refresh");</script>'
        )
        
    except Exception as e:
        return htmx_error_response(f"Error updating beneficiary status: {str(e)}")


# TopUp views
class TopUpTemplateView(LoginRequiredMixin, NotificationMixin, TemplateView):
    """Template view for topups list page"""
    template_name = 'pages/core/membership/topups/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['status_choices'] = TopUp.STATUS_CHOICES
        
        # Add statistics
        context['total_topups'] = TopUp.objects.count()
        context['pending_topups'] = TopUp.objects.filter(status='P').count()
        context['approved_topups'] = TopUp.objects.filter(status='A').count()
        context['rejected_topups'] = TopUp.objects.filter(status='R').count()
        
        return context


class TopUpListView(LoginRequiredMixin, NotificationMixin, ListView):
    """List view for topups"""
    model = TopUp
    template_name = 'pages/core/membership/partials/topup-list/datatable.html'
    context_object_name = 'topups'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = TopUp.objects.select_related('member', 'account')
        
        # Filter by member if specified
        member_id = self.request.GET.get('member')
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search functionality
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(member__name__icontains=search) |
                Q(member__membership_number__icontains=search) |
                Q(mobile_number__icontains=search) |
                Q(bank_reference__icontains=search) |
                Q(amount__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['status_choices'] = TopUp.STATUS_CHOICES
        
        # Add statistics
        context['total_topups'] = TopUp.objects.count()
        context['pending_topups'] = TopUp.objects.filter(status='P').count()
        context['approved_topups'] = TopUp.objects.filter(status='A').count()
        context['rejected_topups'] = TopUp.objects.filter(status='R').count()
        
        return context


class TopUpDetailView(LoginRequiredMixin, NotificationMixin, DetailView):
    """Detail view for a specific topup"""
    model = TopUp
    template_name = 'pages/core/membership/topups/details.html'
    context_object_name = 'topup'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add related data
        context['member'] = self.object.member
        context['account'] = self.object.account
        
        return context


class TopUpCreateView(LoginRequiredMixin, NotificationMixin, CreateView):
    """Create new topup view (rendered in modal)"""
    model = TopUp
    template_name = 'pages/core/membership/partials/topup-list/form.html'
    form_class = TopUpForm
    
    def get_success_url(self):
        return reverse_lazy('membership:topups_detail', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        """Handle successful form submission with HTMX response"""
        self.object = form.save()
        self.success_notification(self.request, f"TopUp of {self.object.amount} for '{self.object.member.name}' created successfully!")
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
        context['modal_title'] = 'Create New TopUp'
        context['submit_text'] = 'Create TopUp'
        return context


class TopUpUpdateView(LoginRequiredMixin, NotificationMixin, UpdateView):
    """Update topup view (rendered in modal)"""
    model = TopUp
    template_name = 'pages/core/membership/partials/topup-list/form.html'
    form_class = TopUpForm
    
    def get_success_url(self):
        return reverse_lazy('membership:topups_detail', kwargs={'pk': self.object.id})
    
    def form_valid(self, form):
        self.object = form.save()
        """Handle successful form submission with HTMX response"""
        self.success_notification(self.request, f"TopUp of {self.object.amount} for '{self.object.member.name}' updated successfully!")
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
        context['modal_title'] = f'Update TopUp: {self.object.amount} for {self.object.member.name}'
        context['submit_text'] = 'Update TopUp'
        return context


# Additional utility views for HTMX interactions

def topup_search_suggestions(request):
    """HTMX endpoint for topup search suggestions"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    topups = TopUp.objects.filter(
        Q(member__name__icontains=query) | 
        Q(member__membership_number__icontains=query) |
        Q(mobile_number__icontains=query) |
        Q(bank_reference__icontains=query) |
        Q(amount__icontains=query)
    ).select_related('member')[:10]
    
    suggestions = [
        {
            'id': topup.id,
            'amount': str(topup.amount),
            'member_name': topup.member.name,
            'member_number': topup.member.membership_number,
            'status': topup.get_status_display()
        }
        for topup in topups
    ]
    
    return JsonResponse({'suggestions': suggestions})


def topup_quick_stats(request, topup_id):
    """HTMX endpoint for topup quick statistics"""
    topup = get_object_or_404(TopUp, id=topup_id)
    
    # Calculate statistics
    member_topups_count = TopUp.objects.filter(member=topup.member).count()
    member_total_amount = TopUp.objects.filter(member=topup.member, status='A').aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    context = {
        'topup': topup,
        'member_topups_count': member_topups_count,
        'member_total_amount': member_total_amount,
        'net_amount': topup.net_amount,
    }
    
    return render(request, 'pages/core/membership/partials/topup_quick_stats.html', context)


def toggle_topup_status(request, topup_id):
    """HTMX endpoint to toggle topup status"""
    if request.method != 'POST':
        return htmx_error_response("Invalid request method.")
    
    try:
        topup = get_object_or_404(TopUp, id=topup_id)
        
        # Toggle status
        if topup.status == 'A':
            topup.status = 'P'
            status_text = 'set to pending'
        elif topup.status == 'P':
            topup.status = 'A'
            status_text = 'approved'
        else:
            topup.status = 'P'
            status_text = 'set to pending'
        
        topup.save()
        
        return htmx_success_response(
            f"TopUp of {topup.amount} for '{topup.member.name}' has been {status_text}.",
            f'<script>htmx.trigger("#topup-list", "refresh");</script>'
        )
        
    except Exception as e:
        return htmx_error_response(f"Error updating topup status: {str(e)}")


# Application views
class ApplicationListView(LoginRequiredMixin, NotificationMixin, ListView):
    """List view for member applications"""
    model = ApplicantMember
    template_name = 'pages/core/membership/application_list.html'
    context_object_name = 'applications'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ApplicantMember.objects.all()
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search functionality
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(firstname__icontains=search) |
                Q(surname__icontains=search) |
                Q(application_number__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset.order_by('-created_at')
