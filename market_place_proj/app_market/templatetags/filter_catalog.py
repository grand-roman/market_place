import math
import re

from django import template
from django.core.cache import cache
from django.db.models import Count, F, Max, Min
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language

from app_market.models import Category, Good, Seller

from market_place_proj.constants import CacheTime, CounterSettings


register = template.Library()


@register.inclusion_tag('app_market/widgets/category/filter_category.html')
def get_filter():
    """
    Вывод товаров на странице каталогов
    :return: context
    """

    price = dict()
    seller = Seller.objects.values('title', 'title_en').all()
    price['max'] = math.ceil(seller.aggregate(max=Max('catalog__price')).get('max'))
    price['min'] = math.floor(seller.aggregate(min=Min('catalog__price')).get('min'))
    context = {'seller': seller, 'price': price}
    return context


@register.inclusion_tag('app_market/widgets/category/popular_tag.html')
def get_tags(slug: str):
    """
    Вывод тэгов на странице каталогов
    :return: context
    """
    qs = cache.get(f'tags:{get_language()}:{slug}')
    if qs:
        return qs
    cat = get_object_or_404(Category, slug=slug)
    if not cat.is_root_node():
        goods = cat.good.filter(soft_delete=False).prefetch_related('good').all()
    else:
        goods = Good.objects.filter(category__in=cat.get_children(), soft_delete=False).all()
    qs = goods.prefetch_related(
        'tag').filter(
        tag__isnull=False).annotate(
        tag__title=F(f'tag__title_{get_language()}')).values(
        'tag__title').annotate(
        count=Count('tag__title')).order_by(
        '-count')
    context = dict(tags=qs[:CounterSettings.TAG_COUNT], slug=slug)
    cache.set(f'tags:{get_language()}:{slug}', context, CacheTime.TAGS_FOR_CATALOG_PAGE)
    return context


@register.inclusion_tag('app_market/widgets/category/sorted_category.html')
def get_sorted(request):
    """
    Сортировка товара в категории
    :return: context
    """
    sort_dict = {
        'popular': 'popular',
        'price': 'price',
        'review': 'review',
        'new': 'new',
    }

    get_page = request.get_full_path().split('/')[-1]
    if len(request.GET.dict()) == 1 and '?sorted=' in get_page:
        sort_key = '?sorted='
        res = request.GET.get('sorted')
        request.session['sorted'] = res
        for k, v in sort_dict.items():
            if v.endswith(res):
                sort_dict[k] = sort_key + 'rev_' + v
            else:
                sort_dict[k] = sort_key + v
        return {'get_sort': sort_dict, 'request': request}
    else:
        res = request.GET.get('sorted')
        request.session['sorted'] = res
        if '?' not in get_page:
            get_page = '?'
            sort_key = 'sorted='
        else:
            sort_key = "&sorted="
        for k, v in sort_dict.items():
            sort_dict[k] = sort_key + v

        check_filter = ''.join(re.findall(r'{sort_key}(\S+)'.format(sort_key=sort_key), get_page))
        if check_filter in ['popular', 'price', 'review', 'new']:
            sort_dict[check_filter] = f'{sort_key}' + 'rev_' + check_filter
            get_page = re.sub(r'{sort_key}(\S+)'.format(sort_key=sort_key), '', get_page)
        elif check_filter in ['rev_popular', 'rev_price', 'rev_review', 'rev_new']:
            sort_dict[check_filter] = f'{sort_key}' + re.sub(r'rev_', '', check_filter)
            get_page = re.sub(r'{sort_key}(\S+)'.format(sort_key=sort_key), '', get_page)

        context = {
            'get_page': get_page,
            'get_sort': sort_dict,
            'request': request
        }
        return context
