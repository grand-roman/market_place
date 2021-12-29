from django import template
from django.core.cache import cache

from app_market.models import Category

from market_place_proj.constants import CacheTime


register = template.Library()


@register.inclusion_tag('base_part/widgets/categories.html')
def get_categories():
    """
    Вывод категорий в header
    :return: context
    """
    category = cache.get('category')
    if not category:
        category = Category.objects.filter(soft_delete=False).all()
        cache.set('category', category, CacheTime.SIDEBARS)
    context = {'categories': category}

    return context


@register.inclusion_tag('base_part/widgets/search_categories.html')
def get_search_categories():
    """
    Вывод категорий в header
    :return: context
    """
    category = cache.get('category')
    if not category:
        category = Category.objects.filter(soft_delete=False).all()
        cache.set('category', category, CacheTime.SIDEBARS)
    context = {'categories': category}

    return context
