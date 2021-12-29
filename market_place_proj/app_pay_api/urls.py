from django.urls import path

from app_pay_api.views import PayApiView


urlpatterns = [
    path('pay/', PayApiView.as_view(), name='pay_create'),
]
