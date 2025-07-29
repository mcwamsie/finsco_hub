from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json

from configurations.models import Member, Service, ServiceProvider
from membership.models import TopUp, Beneficiary
from services.models import Claim, ServiceRequest
from accounting.models import MemberAccount, MemberTransaction


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """Dashboard view for authenticated users with enterprise-level metrics"""
    template_name = 'pages/core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Date ranges for analytics
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        last_7_days = today - timedelta(days=7)
        last_year = today - timedelta(days=365)
        
        # Member Statistics
        total_members = Member.objects.count()
        active_members = Member.objects.filter(status='A').count()
        new_members_30d = Member.objects.filter(date_joined__gte=last_30_days).count()
        
        # Member type distribution
        member_type_stats = Member.objects.values('type').annotate(
            count=Count('id'),
            name=Count('type')
        ).order_by('type')
        
        # Financial Statistics
        total_balance = MemberAccount.objects.aggregate(
            total=Sum('balance')
        )['total'] or 0
        
        total_topups = TopUp.objects.filter(status='S').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_claims_paid = Claim.objects.filter(status='P').aggregate(
            total=Sum('paid_to_provider_amount') + Sum('paid_to_member_amount')
        )['total'] or 0
        
        # Service Statistics
        total_claims = Claim.objects.count()
        pending_claims = Claim.objects.filter(status__in=['N', 'U']).count()
        approved_claims = Claim.objects.filter(status='A').count()
        
        total_service_requests = ServiceRequest.objects.count()
        pending_requests = ServiceRequest.objects.filter(status='P').count()
        
        # Recent Activity
        recent_members = Member.objects.select_related('default_package').order_by('-date_joined')[:5]
        recent_topups = TopUp.objects.select_related('member').filter(
            status='S'
        ).order_by('-completed_date')[:5]
        recent_claims = Claim.objects.select_related('beneficiary', 'provider').order_by('-created_at')[:5]
        
        # Chart Data - Monthly trends
        monthly_data = self.get_monthly_trends()
        
        # Top performing providers
        top_providers = ServiceProvider.objects.annotate(
            claim_count=Count('claim'),
            total_amount=Sum('claim__paid_to_provider_amount')
        ).filter(claim_count__gt=0).order_by('-total_amount')[:5]
        
        # Member growth chart data
        member_growth_data = self.get_member_growth_data()
        
        # Financial overview chart data
        financial_overview = self.get_financial_overview()
        
        context.update({
            'page_title': 'Enterprise Dashboard',
            'breadcrumbs': [
                {'name': 'Home', 'url': '/'},
                {'name': 'Dashboard', 'url': None, 'active': True}
            ],
            
            # Key Metrics
            'total_members': total_members,
            'active_members': active_members,
            'new_members_30d': new_members_30d,
            'member_growth_rate': round((new_members_30d / max(total_members - new_members_30d, 1)) * 100, 1),
            
            'total_balance': total_balance,
            'total_topups': total_topups,
            'total_claims_paid': total_claims_paid,
            'avg_member_balance': round(total_balance / max(total_members, 1), 2),
            
            'total_claims': total_claims,
            'pending_claims': pending_claims,
            'approved_claims': approved_claims,
            'claims_approval_rate': round((approved_claims / max(total_claims, 1)) * 100, 1),
            
            'total_service_requests': total_service_requests,
            'pending_requests': pending_requests,
            'request_completion_rate': round(((total_service_requests - pending_requests) / max(total_service_requests, 1)) * 100, 1),
            
            # Recent Activity
            'recent_members': recent_members,
            'recent_topups': recent_topups,
            'recent_claims': recent_claims,
            
            # Chart Data
            'monthly_trends': json.dumps(monthly_data),
            'member_growth_data': json.dumps(member_growth_data),
            'financial_overview': json.dumps(financial_overview),
            'member_type_distribution': json.dumps(list(member_type_stats)),
            
            # Top Performers
            'top_providers': top_providers,
            
            # Status Indicators
            'system_health': self.get_system_health(),
        })
        return context
    
    def get_monthly_trends(self):
        """Get monthly trends for the last 12 months"""
        today = timezone.now().date()
        months = []
        
        for i in range(12):
            month_start = today.replace(day=1) - timedelta(days=30*i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            # Get data for this month
            members_count = Member.objects.filter(
                date_joined__range=[month_start, month_end]
            ).count()
            
            topups_amount = TopUp.objects.filter(
                completed_date__range=[month_start, month_end],
                status='S'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            claims_amount = Claim.objects.filter(
                created_at__range=[month_start, month_end],
                status='P'
            ).aggregate(total=Sum('paid_to_provider_amount'))['total'] or 0
            
            months.append({
                'month': month_start.strftime('%b %Y'),
                'members': members_count,
                'topups': float(topups_amount),
                'claims': float(claims_amount)
            })
        
        return list(reversed(months))
    
    def get_member_growth_data(self):
        """Get member growth data for the last 30 days"""
        today = timezone.now().date()
        growth_data = []
        
        for i in range(30):
            date = today - timedelta(days=i)
            count = Member.objects.filter(date_joined=date).count()
            growth_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        
        return list(reversed(growth_data))
    
    def get_financial_overview(self):
        """Get financial overview data"""
        today = timezone.now().date()
        last_7_days = today - timedelta(days=7)
        
        # Daily financial data for the last 7 days
        financial_data = []
        
        for i in range(7):
            date = today - timedelta(days=i)
            
            topups = TopUp.objects.filter(
                completed_date__date=date,
                status='S'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            claims = Claim.objects.filter(
                created_at__date=date,
                status='P'
            ).aggregate(total=Sum('paid_to_provider_amount'))['total'] or 0
            
            financial_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'topups': float(topups),
                'claims': float(claims),
                'net': float(topups - claims)
            })
        
        return list(reversed(financial_data))
    
    def get_system_health(self):
        """Get system health indicators"""
        today = timezone.now().date()
        
        # Calculate various health metrics
        failed_topups = TopUp.objects.filter(
            status='F',
            created_at__date=today
        ).count()
        
        total_topups_today = TopUp.objects.filter(
            created_at__date=today
        ).count()
        
        pending_claims_old = Claim.objects.filter(
            status__in=['N', 'U'],
            created_at__lt=timezone.now() - timedelta(days=7)
        ).count()
        
        return {
            'topup_success_rate': round(((total_topups_today - failed_topups) / max(total_topups_today, 1)) * 100, 1),
            'old_pending_claims': pending_claims_old,
            'system_status': 'healthy' if failed_topups < 5 and pending_claims_old < 10 else 'warning'
        }