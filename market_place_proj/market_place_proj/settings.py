import os

import environ


root = environ.Path(__file__) - 2
setting_root = environ.Path(__file__) - 3

BASE_DIR = root()

env = environ.Env()
environ.Env.read_env(env_file=setting_root('.env'))

SECRET_KEY = env.str('SECRET_KEY', 'SECRET_KEY')
DEBUG = env.bool('DEBUG', False)
ALLOWED_HOSTS = env.str('ALLOWED_HOSTS', default='').split(' ')
INTERNAL_IPS = ['127.0.0.1']

INSTALLED_APPS = [
    'modeltranslation',
    'django.contrib.admin',
    'admin_extension.apps.AdminExtensionConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'view_breadcrumbs',
    'mptt',
    'rest_framework',

    'app_users.apps.AppUsersConfig',
    'app_market.apps.AppMarketConfig',
    'app_pay_api',
]

AUTH_USER_MODEL = 'app_users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'market_place_proj.urls'

TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # 'django.core.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'market_place_proj.wsgi.application'

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(setting_root(), 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'megano',
            'USER': 'django',
            'PASSWORD': 'Django2021',
            'HOST': '127.0.0.1',
            'PORT': '5432',
        }
    }

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

LOCALE_PATHS = (os.path.join(BASE_DIR, 'locale'),)
LANGUAGE_CODE = 'en-us'
LANGUAGES = [
    ('ru', 'Русский'),
    ('en', 'English')
]

TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
# STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_URL = '/auth/logout/'

MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'
MODELTRANSLATION_TRANSLATION_REGISTRY = 'market_place_proj.translation'

CACHE_ROOT = os.path.join(BASE_DIR, 'cache/')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': CACHE_ROOT,
    }
}

# добавим DDT в дебугу
if DEBUG:
    INTERNAL_IPS = ['127.0.0.1', ]
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(-2, 'debug_toolbar.middleware.DebugToolbarMiddleware')

BREADCRUMBS_TEMPLATE = 'base_part/widgets/breadcrumbs.html'

good_cache_key_list = []

PAYMENT_HOST = env.str('PAYMENT_HOST', 'http://127.0.0.1:8000')
RMQ_HOST = env.str('RMQ_HOST', '127.0.0.1')
RMQ_PORT = env.str('RMQ_PORT', '5612')

try:
    from market_place_proj.settings_local import *  # noqa
except ImportError:
    pass

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'email@gmail.com'
EMAIL_HOST_PASSWORD = '123456'
EMAIL_PORT = 587

# redis
REDIS_HOST = env.str('REDIS_HOST', '127.0.0.1')
REDIS_PORT = '6379'
CELERY_BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_RESULT_BACKEND = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
CELERY_ACCEPT_CONTENT = ['application/json', 'yaml']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'myformatter': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'myformatter',
        },
        'import': {
            'formatter': 'myformatter',
            'class': 'logging.FileHandler',
            'filename': 'info_import.log',
        },
        'root_handler': {
            'formatter': 'myformatter',
            'class': 'logging.FileHandler',
            'filename': 'megano.log',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'about_import': {
            'handlers': ['import'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
