from django.utils.deprecation import MiddlewareMixin
from .signals import set_current_request
from .utils import log_system_event
import traceback
import time


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware to capture request information for audit logging
    """
    
    def process_request(self, request):
        """Store request in thread-local storage for signal handlers"""
        set_current_request(request)
        
        # Store request start time for performance monitoring
        request._audit_start_time = time.time()
        
        return None
    
    def process_response(self, request, response):
        """Log response information if needed"""
        # Calculate request processing time
        if hasattr(request, '_audit_start_time'):
            processing_time = time.time() - request._audit_start_time
            
            # Log slow requests (over 5 seconds)
            if processing_time > 5.0:
                log_system_event(
                    event_type='PERFORMANCE',
                    title='Slow Request Detected',
                    description=f'Request to {request.path} took {processing_time:.2f} seconds',
                    user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                    request=request,
                    module='middleware'
                )
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions that occur during request processing"""
        log_system_event(
            event_type='ERROR',
            title=f'{exception.__class__.__name__}: {str(exception)}',
            description=f'Exception occurred while processing {request.method} {request.path}',
            user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
            request=request,
            module='middleware',
            function_name=request.resolver_match.func.__name__ if request.resolver_match else 'unknown',
            stack_trace=traceback.format_exc()
        )
        
        return None  # Let Django handle the exception normally


class SecurityAuditMiddleware(MiddlewareMixin):
    """
    Middleware for security-related audit logging
    """
    
    def process_request(self, request):
        """Check for suspicious activity"""
        # Log requests with suspicious patterns
        suspicious_patterns = [
            'admin', 'wp-admin', 'phpmyadmin', '.env', 'config',
            'backup', 'sql', 'dump', 'shell', 'cmd'
        ]
        
        path_lower = request.path.lower()
        if any(pattern in path_lower for pattern in suspicious_patterns):
            log_system_event(
                event_type='SECURITY',
                title='Suspicious Request Pattern',
                description=f'Potentially suspicious request to {request.path}',
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                request=request,
                module='security'
            )
        
        # Log requests with unusual user agents
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        suspicious_agents = ['bot', 'crawler', 'spider', 'scan', 'hack', 'exploit']
        
        if any(agent in user_agent for agent in suspicious_agents):
            log_system_event(
                event_type='SECURITY',
                title='Suspicious User Agent',
                description=f'Request with suspicious user agent: {user_agent[:200]}',
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                request=request,
                module='security'
            )
        
        return None