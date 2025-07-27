# settings.py - VitalSuite Medical Aid Management System
import os
from pathlib import Path
from decouple import config
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
APP_NAME = config('APP_NAME', default='Finsco Hub')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-development-key-change-in-production-abcdefghijklmnopqrstuvwxyz0123456789')
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'import_export',
    # 'simple_history',
    'phonenumber_field',
    'active_link',
    # 'crispy_forms',
    # 'crispy_bootstrap4',
    'sequences',
    'widget_tweaks',
    'django_extensions',
    'django_celery_beat',
    'django_celery_results',
    'channels',
    'drf_yasg',
    'django_countries',
    'django_tables2',
    'django_select2',
    "audit",
]

LOCAL_APPS = [
    # "fisco_hub_8d.users",
    'authentication.apps.AuthenticationConfig',
    'configurations.apps.ConfigurationsConfig',
    # 'membership.apps.MembershipConfig',
    'services.apps.ServicesConfig',
    'finance.apps.FinanceConfig',
    'membership.apps.MembershipConfig',
    'accounting.apps.AccountingConfig',
    # 'reports.apps.ReportsConfig',
    # 'api.apps.ApiConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # 'whitenoise.middleware.WhiteNoiseMiddleware',
    # 'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.AuditMiddleware',
    'audit.middleware.SecurityAuditMiddleware',
    # 'configurations.middleware.TimezoneMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'fisco_hub_8d.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'configurations.global_context.application_settings',
                # 'configurations.context_processors.global_settings',
                # 'configurations.context_processors.user_permissions',
            ],
        },
    },
]

WSGI_APPLICATION = 'fisco_hub_8d.wsgi.application'
ASGI_APPLICATION = 'fisco_hub_8d.asgi.application'

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME', default='vitalsuite_db'),
        'USER': config('DB_USER', default='vitalsuite_user'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
    }
}

# Add PostgreSQL-specific options only when using PostgreSQL
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    DATABASES['default']['OPTIONS'] = {
        'client_encoding': 'UTF8',
    }

# Custom User Model
# AUTH_USER_MODEL = 'authentication.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-us')
TIME_ZONE = config('TIME_ZONE', default='Africa/Harare')
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('sn', 'Shona'),
    ('nd', 'Ndebele'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': 'vitalsuite',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# API Documentation
# SPECTACULAR_SETTINGS = {
#     'TITLE': 'VitalSuite API',
#     'DESCRIPTION': 'Comprehensive Medical Aid Management System API',
#     'VERSION': '1.0.0',
#     'SERVE_INCLUDE_SCHEMA': False,
#     'COMPONENT_SPLIT_REQUEST': True,
#     'SCHEMA_PATH_PREFIX': '/api/v1/',
# }

# CORS Configuration
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=False, cast=bool)

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=not DEBUG, cast=bool)

# Cookie Security Settings
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=not DEBUG, cast=bool)

# Additional security settings for production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

# Session Configuration
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@vitalsuite.com')

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'send-daily-sms-reports': {
        'task': 'configurations.tasks.send_daily_sms_reports',
        'schedule': timedelta(hours=24),
    },
    'cleanup-old-gateway-requests': {
        'task': 'configurations.tasks.cleanup_old_gateway_requests',
        'schedule': timedelta(days=7),
    },
    'refresh-expiring-payment-tokens': {
        'task': 'configurations.tasks.refresh_expiring_payment_tokens',
        'schedule': timedelta(hours=1),
    },
    'process-pending-adjudications': {
        'task': 'services.tasks.process_pending_adjudications',
        'schedule': timedelta(minutes=30),
    },
    'check-document-expiry': {
        'task': 'configurations.tasks.check_document_expiry',
        'schedule': timedelta(hours=12),
    },
    'calculate-agent-commissions': {
        'task': 'configurations.tasks.calculate_agent_commissions',
        'schedule': timedelta(days=1),
    },
}

# Redis Configuration
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/1')

# Caching Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'vitalsuite',
        'TIMEOUT': 300,
    }
}

PAGINATE_BY = config('PAGINATE_BY', default=1, cast=int)
# Channels Configuration (WebSocket)
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             'hosts': [config('REDIS_URL', default='redis://localhost:6379/2')],
#         },
#     },
# }

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'vitalsuite.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'vitalsuite': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'services.adjudication': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'configurations.signals': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'root': {
        'handlers': ['error_file'],
        'level': 'ERROR',
    },
}

# File Upload Configuration
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Import/Export Configuration
IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_SKIP_ADMIN_LOG = False
IMPORT_EXPORT_TMP_STORAGE_CLASS = 'import_export.tmp_storages.TempFolderStorage'

# Phone Number Configuration
PHONENUMBER_DEFAULT_REGION = 'ZW'
# PHONENUMBER_DEFAULT_FORMAT = 'INTERNATIONAL'
AUTH_USER_MODEL = 'authentication.User'
# Crispy Forms Configuration
# CRISPY_TEMPLATE_PACK = 'bootstrap4'

# Custom Fisco Hub Settings
FISCO_HUB_SUITE_SETTINGS = {
    'SYSTEM_NAME': 'Fisco Hub',
    'SYSTEM_VERSION': '1.0.0',
    'COMPANY_NAME': config('COMPANY_NAME', default='Medical Aid Society'),
    'SUPPORT_EMAIL': config('SUPPORT_EMAIL', default='support@vitalsuite.com'),
    'SUPPORT_PHONE': config('SUPPORT_PHONE', default='+263242123456'),

    # Business Rules
    'DEFAULT_CURRENCY': config('DEFAULT_CURRENCY', default='USD'),
    'MAX_CLAIM_AGE_DAYS': config('MAX_CLAIM_AGE_DAYS', default=365, cast=int),
    'AUTO_ADJUDICATION_LIMIT': config('AUTO_ADJUDICATION_LIMIT', default=5000, cast=float),
    'HIGH_VALUE_CLAIM_THRESHOLD': config('HIGH_VALUE_CLAIM_THRESHOLD', default=10000, cast=float),

    # SMS Configuration
    'SMS_GATEWAY_URL': config('SMS_GATEWAY_URL', default=''),
    'SMS_USERNAME': config('SMS_USERNAME', default=''),
    'SMS_PASSWORD': config('SMS_PASSWORD', default=''),
    'SMS_SENDER_ID': config('SMS_SENDER_ID', default='VitalSuite'),

    # Payment Gateway Configuration
    'PAYMENT_GATEWAY_URL': config('PAYMENT_GATEWAY_URL', default=''),
    'PAYMENT_GATEWAY_LOGIN_URL': config('PAYMENT_GATEWAY_LOGIN_URL', default=''),
    'PAYMENT_GATEWAY_USERNAME': config('PAYMENT_GATEWAY_USERNAME', default=''),
    'PAYMENT_GATEWAY_PASSWORD': config('PAYMENT_GATEWAY_PASSWORD', default=''),
    'PAYMENT_GATEWAY_MERCHANT_ID': config('PAYMENT_GATEWAY_MERCHANT_ID', default=''),

    # Notification Settings
    'ENABLE_SMS_NOTIFICATIONS': config('ENABLE_SMS_NOTIFICATIONS', default=True, cast=bool),
    'ENABLE_EMAIL_NOTIFICATIONS': config('ENABLE_EMAIL_NOTIFICATIONS', default=True, cast=bool),
    'NOTIFICATION_RETRY_ATTEMPTS': config('NOTIFICATION_RETRY_ATTEMPTS', default=3, cast=int),

    # Security Settings
    'PASSWORD_RESET_TIMEOUT': config('PASSWORD_RESET_TIMEOUT', default=3600, cast=int),
    'LOGIN_ATTEMPT_LIMIT': config('LOGIN_ATTEMPT_LIMIT', default=5, cast=int),
    'LOGIN_ATTEMPT_TIMEOUT': config('LOGIN_ATTEMPT_TIMEOUT', default=900, cast=int),

    # Feature Flags
    'ENABLE_MOBILE_API': config('ENABLE_MOBILE_API', default=True, cast=bool),
    'ENABLE_PROVIDER_PORTAL': config('ENABLE_PROVIDER_PORTAL', default=True, cast=bool),
    'ENABLE_MEMBER_PORTAL': config('ENABLE_MEMBER_PORTAL', default=True, cast=bool),
    'ENABLE_BATCH_PROCESSING': config('ENABLE_BATCH_PROCESSING', default=True, cast=bool),
}

# Admin Configuration
# ADMIN_SITE_HEADER = 'VitalSuite Administration'
# ADMIN_SITE_TITLE = 'VitalSuite Admin'
# ADMIN_INDEX_TITLE = 'Welcome to VitalSuite Administration'

# Development Settings
if DEBUG:
    # Debug Toolbar
    if config('USE_DEBUG_TOOLBAR', default=False, cast=bool):
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
        INTERNAL_IPS = ['127.0.0.1', '::1']

    # Django Extensions
    GRAPH_MODELS = {
        'all_applications': True,
        'group_models': True,
    }

# Production Settings
if not DEBUG:
    # Security enhancements for production
    USE_TZ = True

    # Disable browsable API in production
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
        'rest_framework.renderers.JSONRenderer',
    ]

    # Production logging
    LOGGING['handlers']['file']['level'] = 'WARNING'
    LOGGING['loggers']['django']['level'] = 'WARNING'

# Testing Configuration
import sys
if 'test' in sys.argv or 'pytest' in sys.modules:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }

    # Use dummy cache for tests
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }


    # Disable migrations for faster tests
    class DisableMigrations:
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None


    MIGRATION_MODULES = DisableMigrations()

# Authentication URLs
LOGIN_URL = 'authentication:login'
LOGIN_REDIRECT_URL = 'configurations:dashboard'
LOGOUT_REDIRECT_URL = 'authentication:login'

# Ensure logs directory exists
import sys

if not (BASE_DIR / 'logs').exists():
    os.makedirs(BASE_DIR / 'logs', exist_ok=True)