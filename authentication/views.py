from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.cache import cache
from django.conf import settings
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from datetime import datetime
import json

from django.views.generic import FormView, TemplateView

from .forms import CustomLoginForm, EmailLoginForm, EmailVerificationForm, generate_verification_code
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginTemplateView(TemplateView):
    template_name = 'pages/auth/login.html'

    def get_context_data(self, **kwargs):
        context = super(LoginTemplateView, self).get_context_data(**kwargs)
        context['email_form'] = EmailLoginForm()
        context['login_form'] = CustomLoginForm()
        return context

class CustomLoginView(LoginView):
    """Extended login view with username/email and password"""
    form_class = CustomLoginForm
    template_name = 'partial/auth/login/login-form.html'
    success_url = reverse_lazy('configurations:dashboard')
    
    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if remember_me:
            # Set session to expire in 30 days
            self.request.session.set_expiry(30 * 24 * 60 * 60)
        else:
            # Set session to expire when browser closes
            self.request.session.set_expiry(0)
        
        messages.success(self.request, 'Successfully logged in!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username/email or password.')
        return super().form_invalid(form)


class EmailLoginView(FormView):
    """Email-only login view that sends verification code"""
    template_name = 'partial/auth/login/email-form.html'
    
    def get(self, request, *args, **kwargs):
        form = EmailLoginForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = form.get_user()
            
            if user:
                # Generate verification code
                try:
                    code = generate_verification_code()

                    # Store code in cache for 10 minutes
                    cache_key = f"email_verification_{email}"
                    cache.set(cache_key, code, 600)  # 10 minutes

                    # Send email
                    self.send_verification_email(email, code, user)

                    # Store email in session for verification step
                    request.session['verification_email'] = email
                    request.session['remember_me'] = form.cleaned_data.get('remember_me', False)

                    # messages.success(request, f'Verification code sent to {email}')
                    # return redirect('authentication:email_verify')
                    return render(request, "partial/auth/login/verify-email.html", {"form":EmailVerificationForm(initial={'email': email})})

                except Exception as e:
                    form.add_error(None, f"Failed to send verification code: {e}")
                    return self.form_invalid(form)
        
        return render(request, self.template_name, {'form': form})

    def send_verification_email(self, email, code, user):
        """Send verification code email using HTML template"""
        subject = 'Your Fisco Hub Verification Code'
        
        # Render HTML email template
        html_message = render_to_string('emails/verification_code.html', {
            'verification_code': code,
            'email': email,
            'current_year': timezone.now().year,
        })
        
        # Create plain text version
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log the error in production
            print(f"Error sending email: {e}")


class EmailVerificationView(FormView):
    """View for verifying email code"""
    template_name = 'partial/auth/login/verify-email.html'
    
    def get(self, request, *args, **kwargs):
        email = request.session.get('verification_email')
        if not email:
            messages.error(request, 'No verification session found. Please try again.')
            return redirect('authentication:email_login')
        
        form = EmailVerificationForm(initial={'email': email})
        return render(request, self.template_name, {
            'form': form,
            'email': email
        })
    
    def post(self, request, *args, **kwargs):
        email = request.session.get('verification_email')
        if not email:
            messages.error(request, 'No verification session found. Please try again.')
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse_lazy('authentication:login')
            return response
        
        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            # Check code from cache
            cache_key = f"email_verification_{email}"
            stored_code = cache.get(cache_key)
            
            if stored_code and stored_code == code:
                # Code is valid, log in user
                try:
                    user = User.objects.get(email=email)
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    
                    # Set session expiry based on remember_me
                    remember_me = request.session.get('remember_me', False)
                    if remember_me:
                        request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
                    else:
                        request.session.set_expiry(0)  # Browser close


                    # Clear verification data
                    cache.delete(cache_key)
                    del request.session['verification_email']
                    if 'remember_me' in request.session:
                        del request.session['remember_me']
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    messages.success(request, 'Successfully logged in!')
                    response = HttpResponse(status=204)
                    response["HX-Redirect"] = reverse_lazy('configurations:dashboard')
                    return response

                except User.DoesNotExist:
                    messages.error(request, 'User account not found.')
            else:
                messages.error(request, 'Invalid or expired verification code.')
        
        return render(request, self.template_name, {
            'form': form,
            'email': email
        })
    
    def handle_htmx_request(self, request):
        """Handle HTMX form submission"""
        email = request.session.get('verification_email')
        if not email:
            return JsonResponse({
                'success': False,
                'message': 'No verification session found. Please try again.',
                'redirect': reverse_lazy('authentication:email_login')
            })
        
        form = EmailVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            # Check code from cache
            cache_key = f"email_verification_{email}"
            stored_code = cache.get(cache_key)
            
            if stored_code and stored_code == code:
                # Code is valid, log in user
                try:
                    user = User.objects.get(email=email)
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    
                    # Set session expiry based on remember_me
                    remember_me = request.session.get('remember_me', False)
                    if remember_me:
                        request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
                    else:
                        request.session.set_expiry(0)  # Browser close
                    
                    # Clear verification data
                    cache.delete(cache_key)
                    del request.session['verification_email']
                    if 'remember_me' in request.session:
                        del request.session['remember_me']
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Successfully logged in!',
                        'redirect': reverse_lazy('configurations:dashboard')
                    })
                    
                except User.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'errors': {'code': ['User account not found.']}
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': {'code': ['Invalid or expired verification code.']}
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })


class ResendCodeView(View):
    """View to resend verification code"""
    
    def post(self, request):
        email = request.session.get('verification_email')
        if not email:
            return JsonResponse({
                'success': False,
                'message': 'No verification session found.'
            })
        
        try:
            user = User.objects.get(email=email)
            
            # Generate new verification code
            code = generate_verification_code()
            
            # Store code in cache for 10 minutes
            cache_key = f"email_verification_{email}"
            cache.set(cache_key, code, 600)  # 10 minutes
            
            # Send email
            email_login_view = EmailLoginView()
            email_login_view.send_verification_email(email, code, user)
            
            return JsonResponse({
                'success': True,
                'message': f'New verification code sent to {email}'
            })
            
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'User account not found.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'Failed to send verification code. Please try again.'
            })
