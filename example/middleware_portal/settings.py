import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

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
]

THIRD_PARTY_APPS = [
    'haystack',
    'django_celery_beat',
    'django_celery_results',
]

LOCAL_APPS = [
    'core',
    'authentication',
    'inventory',
    'certificates',
    'askgt',
    'announcements',
    'automation',
    'performance',
    'duty_schedule',
    'ansible_integration',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'authentication.middleware.SessionTrackingMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'middleware_portal.urls'

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
                'core.context_processors.global_context',
                'askgt.context_processors.askgt_categories',
            ],
        },
    },
]

WSGI_APPLICATION = 'middleware_portal.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='middleware_portal'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'tr-tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
    }
}

# Session
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@middleware-portal.com')

# Celery
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Celery Beat
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Haystack (Search)
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch7_backend.Elasticsearch7SearchEngine',
        'URL': config('ELASTICSEARCH_URL', default='http://127.0.0.1:9200/'),
        'INDEX_NAME': 'middleware_portal',
    },
}

# LDAP Settings
LDAP_SERVER_URI = config('LDAP_SERVER_URI', default='ldap://localhost:389')
LDAP_BIND_DN = config('LDAP_BIND_DN', default='')
LDAP_BIND_PASSWORD = config('LDAP_BIND_PASSWORD', default='')
LDAP_USER_SEARCH_BASE = config('LDAP_USER_SEARCH_BASE', default='ou=users,dc=example,dc=com')

# Certificate Management Settings
APPVIEWX_API_URL = config('APPVIEWX_API_URL', default='https://appviewx.example.com/api/v1')
APPVIEWX_API_KEY = config('APPVIEWX_API_KEY', default='')

# AskGT Document Sync Settings
ASKGT_SYNC_ENABLED = config('ASKGT_SYNC_ENABLED', default=True, cast=bool)
ASKGT_SYNC_INTERVAL = config('ASKGT_SYNC_INTERVAL', default=60, cast=int)  # minutes

# Duty Schedule Settings
DUTY_SYNC_ENABLED = config('DUTY_SYNC_ENABLED', default=True, cast=bool)
DUTY_SYNC_INTERVAL = config('DUTY_SYNC_INTERVAL', default=1440, cast=int)  # minutes (daily)

# Ansible Integration Settings
ANSIBLE_TOWER_URL = config('ANSIBLE_TOWER_URL', default='https://tower.example.com')
ANSIBLE_TOWER_USERNAME = config('ANSIBLE_TOWER_USERNAME', default='')
ANSIBLE_TOWER_PASSWORD = config('ANSIBLE_TOWER_PASSWORD', default='')
ANSIBLE_TOWER_TOKEN = config('ANSIBLE_TOWER_TOKEN', default='')
ANSIBLE_SYNC_INTERVAL = config('ANSIBLE_SYNC_INTERVAL', default=60, cast=int)  # minutes

# Logging
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
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'middleware_portal.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'certificates': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'inventory': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'askgt': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'duty_schedule': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'ansible_integration': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
