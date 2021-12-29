from django import template
from django.core.cache import cache

from app_market.models import Good

from market_place_proj.constants import CacheTime


register = template.Library()


@register.simple_tag
def get_hot_prod():
    """
    Вывод категорий в header
    :return: context
    """
    hot_product = cache.get('hot_product')

    if not hot_product:
        hot_product = Good.objects.values('view_count', 'id').order_by('-view_count')
        if hot_product:
            hot_product = hot_product[0].get('id')
        cache.set('hot_product', hot_product, CacheTime.HOT_PRODUCT)
    return hot_product
