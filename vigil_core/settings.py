"""
Django settings for vigil_core project.
Configured for production deployment on Render with PostgreSQL, ASGI & WebSockets.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file (if present)
load_dotenv(BASE_DIR / '.env')

# Add apps directory to Python path
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# ==============================================================================
# Security & Environment Configuration
# ==============================================================================
SECRET_KEY = os.getenv('SECRET_KEY', 'vigil-fallback-secret-key-replace-in-production-env')
DEBUG = os.getenv('DEBUG', 'False').strip().lower() in ['true', '1', 'yes']

# Allowed Hosts Configuration
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,0.0.0.0').split(',') if host.strip()]

# Automatic Render Domain Support
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if '.onrender.com' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.onrender.com')
if DEBUG:
    ALLOWED_HOSTS.extend(['testserver', 'localhost', '127.0.0.1', '0.0.0.0', '*'])

# Deduplicate allowed hosts
ALLOWED_HOSTS = list(set(ALLOWED_HOSTS))

# ==============================================================================
# Application Definition
# ==============================================================================
INSTALLED_APPS = [
    'daphne',  # Daphne ASGI server must be listed before django.contrib.staticfiles
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',  # WhiteNoise runserver integration
    'django.contrib.staticfiles',

    # Third Party Libraries
    'rest_framework',
    'corsheaders',
    'channels',

    # Modular Public Safety Apps (12 Apps + Common)
    'common.apps.CommonConfig',
    'accounts.apps.AccountsConfig',
    'tourists.apps.TouristsConfig',
    'digital_id.apps.DigitalIdConfig',
    'geofencing.apps.GeofencingConfig',
    'incidents.apps.IncidentsConfig',
    'emergency.apps.EmergencyConfig',
    'risk.apps.RiskConfig',
    'maps.apps.MapsConfig',
    'alerts.apps.AlertsConfig',
    'dashboard.apps.DashboardConfig',
    'ai_services.apps.AiServicesConfig',
    'demo.apps.DemoConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # WhiteNoise for high-performance static asset serving
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vigil_core.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'vigil_core.wsgi.application'
ASGI_APPLICATION = 'vigil_core.asgi.application'

# ==============================================================================
# Database Configuration: PostgreSQL is the Primary & Default Engine
# ==============================================================================
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Render or Cloud PostgreSQL via DATABASE_URL
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=(not DEBUG and 'localhost' not in DATABASE_URL and '127.0.0.1' not in DATABASE_URL and 'sqlite' not in DATABASE_URL)
        )
    }
elif os.getenv('DB_NAME') and os.getenv('DB_USER'):
    # Dedicated PostgreSQL parameters
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'vigil_db'),
            'USER': os.getenv('DB_USER', 'vigil_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'vigil_password_2026'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,
            'CONN_HEALTH_CHECKS': True,
        }
    }
else:
    # Local & Single-instance fallback
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model with RBAC Roles
AUTH_USER_MODEL = 'accounts.User'

# ==============================================================================
# Django Channels & WebSocket Layer Configuration
# ==============================================================================
REDIS_URL = os.getenv('REDIS_URL', '')
CHANNEL_LAYER_BACKEND = os.getenv('CHANNEL_LAYER_BACKEND', 'redis' if REDIS_URL else 'inmemory').lower()

if REDIS_URL or CHANNEL_LAYER_BACKEND == 'redis':
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL or 'redis://127.0.0.1:6379/0'],
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer'
        }
    }

# ==============================================================================
# Password Validation
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==============================================================================
# Django REST Framework Configuration
# ==============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# ==============================================================================
# CORS & CSRF Trusted Origins Configuration
# ==============================================================================
raw_cors = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in raw_cors.split(',') if origin.strip()]

raw_csrf = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in raw_csrf.split(',') if origin.strip()]

# Automatically trust Render domains
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)

if 'https://*.onrender.com' not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append('https://*.onrender.com')

CORS_ALLOW_CREDENTIALS = True

# ==============================================================================
# Internationalization
# ==============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# Static Files & WhiteNoise Configuration
# ==============================================================================
STATIC_URL = os.getenv('STATIC_URL', '/static/')
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise Compressed Static Storage for production
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# ==============================================================================
# Media Files (Uploaded incident evidence, QR codes, avatars, CCTV frames)
# ==============================================================================
MEDIA_URL = os.getenv('MEDIA_URL', '/media/')
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth Redirects
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/tourist/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# ==============================================================================
# Production HTTPS & Security Headers (Behind Render Proxy)
# ==============================================================================
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() in ['true', '1']
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ['true', '1']
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() in ['true', '1']

if not DEBUG and SECURE_SSL_REDIRECT:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
