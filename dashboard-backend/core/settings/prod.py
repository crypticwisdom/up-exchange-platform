from .base import *

SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ["*"]

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': env('DATABASE_ENGINE', None),
        'NAME': env('DATABASE_NAME', None),
        'USER': env('DATABASE_USER', None),
        'PASSWORD': env('DATABASE_PASSWORD', None),
        'HOST': env('DATABASE_HOST', None),
        'PORT': env('DATABASE_PORT', None),
        'OPTIONS': {
            'options': f"-c search_path={env('DATABASE_SCHEMA', None)}"
        },
    }
}


