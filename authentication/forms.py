from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import random
import string

User = get_user_model()


class CustomLoginForm(AuthenticationForm):
    """Extended login form with username/email and password"""
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent form-field disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
            'placeholder': 'Enter your username or email',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent form-field disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded form-field disabled:opacity-50 disabled:cursor-not-allowed'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Username or Email'
        self.fields['password'].label = 'Password'
        self.fields['remember_me'].label = 'Remember me for 30 days'


class EmailLoginForm(forms.Form):
    """Email-only login form that sends verification code"""
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'placeholder': 'user@finscohub.com',
            'autocomplete': 'email',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = 'Email Address'
        self.fields['remember_me'].label = 'Remember me for 30 days'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                return email
            except User.DoesNotExist:
                raise ValidationError("No account found with this email address.")
        return email

    def get_user(self):
        """Get the user associated with the email"""
        email = self.cleaned_data.get('email')
        if email:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist:
                return None
        return None


class EmailVerificationForm(forms.Form):
    """Form for verifying email code"""
    code = forms.CharField(
        max_length=6,
        min_length=4,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent form-field disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50 text-center text-lg tracking-widest',
            'placeholder': '0000',
            'autocomplete': 'one-time-code',
            'maxlength': '6',
            'pattern': '[0-9]*',
            'inputmode': 'numeric',
        })
    )
    email = forms.EmailField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].label = 'Verification Code'

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code and not code.isdigit():
            raise ValidationError("Code must contain only numbers.")
        return code


def generate_verification_code():
    """Generate a 4-digit verification code"""
    return ''.join(random.choices(string.digits, k=4))