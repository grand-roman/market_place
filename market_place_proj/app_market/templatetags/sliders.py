from django import template
from django.core.cache import cache
from django.urls import reverse_lazy

from app_market.models import Stock

from market_place_proj.constants import CacheTime


register = template.Library()


@register.inclusion_tag('base_part/slider.html')
def main_slider(request):
    """
    Вывод акций для основного слайдера
    """
    index_url = reverse_lazy('index')
    if request.path != index_url:
        return {}

    stocks = cache.get('slider_stocks',)
    if not stocks:
        stocks = Stock.objects.filter(is_active=True).order_by('sort')[:3]
        cache.set('slider_stocks', stocks, CacheTime.SLIDER)

    context = {'stocks': stocks}
    return context
