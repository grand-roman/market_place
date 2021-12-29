from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

import debug_toolbar


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_users.urls')),
    path('', include('app_market.urls')),
    path('', include('admin_extension.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include('app_pay_api.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# добавим DDT в дебугу
if settings.DEBUG:
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
