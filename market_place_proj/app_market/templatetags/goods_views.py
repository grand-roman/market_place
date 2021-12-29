from django import template
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q, Sum
from django.urls import reverse_lazy

from app_market.models import Good
from app_market.utils import GoodViewService, SaleService


register = template.Library()


@register.inclusion_tag('app_market/widgets/viewed_good_list.html')
@login_required(login_url=reverse_lazy('login'))
def viewed_goods(request, count):
    """
    Тэг возвращает набор просмотренных товаров
    """
    qs = GoodViewService.get_good_view_list(request, count)
    for view in qs:
        if view.good.discount and view.good.discount.active:
            view.good.discounted_price = SaleService.calculate_sale(view.avg_price, view.good.discount)
            view.good.sale = SaleService.get_percent_from_old_price(view.avg_price, view.good.discounted_price)
    return dict(goods=qs)


@register.inclusion_tag('app_market/widgets/shop_cards.html')
def shop_cards(count):
    qs = Good.objects.filter(
        Q(soft_delete=False) & (Q(image__file__isnull=False) | Q(image__link__isnull=False))
    ).prefetch_related(
        'catalog').select_related(
        'image', 'discount', 'category').annotate(
        avg_price=Avg('catalog__price')).annotate(
            popularity_index=Sum('catalog__popularity_index')).order_by(
            '-popularity_index')[:count]
    return dict(goods=qs)
