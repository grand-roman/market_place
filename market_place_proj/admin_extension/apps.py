from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdminExtensionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_extension'
    verbose_name = _('Аdmin extension')
