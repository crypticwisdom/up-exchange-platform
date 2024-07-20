from datetime import timedelta
from .base import *

SECRET_KEY = env('SECRET_KEY')

DEBUG = True

ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "https://exchange.tm-dev.xyz",
    "http://exchange.tm-dev.xyz",
    "http://localhost:8080",
    "http://localhost:80",
    "http://localhost:3000",
    "http://localhost",
    "http://127.0.0.1"
]

# from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-api-key",
]

CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS


# Database
DATABASES = {
    'default': {
        'ENGINE': env('DATABASE_ENGINE', None),
        'NAME': env('DATABASE_NAME', None),
        'USER': env('DATABASE_USER', None),
        'PASSWORD': env('DATABASE_PASSWORD', None),
        'HOST': env('DATABASE_HOST', None),
        'PORT': env('DATABASE_PORT', None),
    },
    'exchange': {
        'ENGINE': env('DATABASE_ENGINE', None),
        'OPTIONS': {
            'options': f"-c search_path={env('EX_DATABASE_SCHEMA', None)}"
        },
        'NAME': env('EX_DATABASE_NAME', None),
        'USER': env('EX_DATABASE_USER', None),
        'PASSWORD': env('EX_DATABASE_PASSWORD', None),
        'HOST': env('EX_DATABASE_HOST', None),
        'PORT': env('EX_DATABASE_PORT', None),
    }

}
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Email
EMAIL_URL = env('EMAIL_URL', None)
X_API_KEY = env('X_API_KEY', None)
FRONTEND_URL = env('FRONTEND_URL', None)

# Simple JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=60),
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer', 'Token',),
}



