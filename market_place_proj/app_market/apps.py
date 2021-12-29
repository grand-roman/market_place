from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AppMarketConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_market'
    verbose_name = _('Аpp market')
