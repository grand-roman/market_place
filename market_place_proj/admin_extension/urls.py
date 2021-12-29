from django.conf.urls import url
from django.contrib.auth.decorators import user_passes_test

from admin_extension.views import admin_settings, import_files


urlpatterns = [
    url('admin-settings', user_passes_test(lambda u: u.is_superuser)(admin_settings), name='admin_settings'),
    url('admin-import', user_passes_test(lambda u: u.is_superuser)(import_files), name='import_goods'),
]
