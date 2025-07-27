from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """Dashboard view for authenticated users"""
    template_name = 'pages/core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Dashboard',
            'breadcrumbs': [
                {'name': 'Home', 'url': '/'},
                {'name': 'Dashboard', 'url': None, 'active': True}
            ]
        })
        return context