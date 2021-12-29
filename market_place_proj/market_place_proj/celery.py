import os

from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'market_place_proj.settings')

app = Celery('import_files',)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
