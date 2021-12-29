import re

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from app_market.models import Seller


class User(AbstractUser):
    """Расширенная модель пользователя.

    Attributes
        full_name: ФИО
        phone: Телефон
        is_email_verified: Флаг подтверждения Email
        avatar: Аватар пользователя
        seller: Продавец
    """
    last_name = None
    first_name = None

    full_name = models.CharField(_('Full name'), max_length=255, blank=True, null=True)
    phone = models.CharField(
        _('Phone'), max_length=12, unique=True, db_index=True
    )
    is_email_verified = models.BooleanField(
        _('Email is verified'), default=False
    )
    avatar = models.ImageField(_('Avatar'), blank=True, upload_to='users/')
    seller = models.ForeignKey(
        Seller, on_delete=models.PROTECT, null=True, blank=True,
        related_name='user', verbose_name=_('Seller')
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        db_table = 'user'
        ordering = ['id']

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return self.full_name if self.full_name else self.username

    def get_phone(self):
        if self.phone:
            t = re.findall(r'\d', str(self.phone))
            return '+{} ({}{}{}) {}{}{}-{}{}-{}{}'.\
                format(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], t[9], t[10])
