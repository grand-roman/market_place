import datetime
import hashlib
import re

from django import template
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Case, Count, DecimalField, F, When
from django.shortcuts import get_object_or_404

from app_market.models import Category, Good
from app_market.utils import CompareService, SaleService

from market_place_proj.constants import CacheTime
from market_place_proj.settings import good_cache_key_list


register = template.Library()

TYPE_OF_FILTER = {'price_range', 'name_product', 'seller', 'in_stock', 'free_shipping'}
TYPE_OF_SORTING = {'popular', 'price', 'review', 'new',
                   'rev_popular', 'rev_price', 'rev_review', 'rev_new'}


@register.inclusion_tag('app_market/widgets/goods.html')
def get_goods(request, slug):
    """
    Вывод товаров на странице каталогов
    :return: context
    """
    goods = cache.get(hashlib.md5(request.get_full_path().encode()).hexdigest())
    if not goods:
        category = get_object_or_404(Category, slug=slug)
        if not category.is_root_node():
            goods = category.good.filter(soft_delete=False). \
                select_related('image', 'discount', 'discount__variants', 'category', 'group'). \
                annotate(avg_price=Avg('catalog__price'), count_review=Count('review')).all()
        else:
            goods = Good.objects.filter(
                category__in=category.get_children(), soft_delete=False).select_related(
                'category', 'group', 'image', 'discount', 'group'
            ).annotate(avg_price=Avg('catalog__price'),
                                                          count_review=Count('review')).all()
        if set(request.GET.dict().keys()) & TYPE_OF_FILTER:
            goods = query_filter(request, goods)
        if request.GET.get('sorted') and set(request.GET.dict().values()) & TYPE_OF_SORTING:
            goods = query_sorted(request, goods)
        goods = query_sale_annotate(goods)
        good_cache_key_list.append(hashlib.md5(request.get_full_path().encode()).hexdigest())
        cache.set(hashlib.md5(request.get_full_path().encode()).hexdigest(), goods, CacheTime.GOOD_CARDS)
    get_page = re.sub(r'(&page=\d+)', '', re.sub(r'[?]', '&', request.get_full_path().split('/')[-1]))
    goods = Paginator(goods, 8).get_page(request.GET.get('page'))

    # добавим идентификаторы из кэша, чтобы менять иконку добавить в сравнение - удалить из сравнения
    # достанем id всех товаров, которые есть в сравнении
    ids = CompareService.get_compare_ids(request)
    context = dict(goods=goods, ids=ids, get_page=get_page)
    return context


@register.inclusion_tag('app_market/widgets/goods.html')
def get_goods_all(request):
    """
    Вывод всех товаров на странице каталогов
    :return: context
    """
    goods = cache.get(hashlib.md5(request.get_full_path().encode()).hexdigest())
    if not goods:
        goods = Good.objects.filter(soft_delete=False).select_related('category', 'image', 'discount').annotate(
            avg_price=Avg(
                'catalog__price'), count_review=Count('review')).all()
        if set(request.GET.dict().keys()) & TYPE_OF_FILTER:
            goods = query_filter(request, goods)
        if request.GET.get('sorted') and set(request.GET.dict().values()) & TYPE_OF_SORTING:
            goods = query_sorted(request, goods)
        goods = goods[:100]
        goods = query_sale_annotate(goods)
        good_cache_key_list.append(hashlib.md5(request.get_full_path().encode()).hexdigest())
        cache.set(hashlib.md5(request.get_full_path().encode()).hexdigest(), goods, CacheTime.GOOD_CARDS)
    get_page = re.sub(r'(&page=\d+)', '', re.sub(r'[?]', '&', request.get_full_path().split('/')[-1]))
    goods = Paginator(goods, 8).get_page(request.GET.get('page'))

    # добавим идентификаторы из кэша, чтобы менять иконку добавить в сравнение - удалить из сравнения
    # достанем id всех товаров, которые есть в сравнении
    ids = CompareService.get_compare_ids(request)
    context = dict(goods=goods, ids=ids, get_page=get_page)
    return context


def query_filter(request, queryset):
    """
    Метод фильтрации товаров по цене, по наименованию, по продавцу, по бесплатной доставке, по наличию
    :param request:
    :param queryset:
    :return:
    """
    req_get = request.GET.dict()
    if req_get.get('price_range'):
        queryset = queryset.filter(avg_price__range=req_get.get('price_range').split(';'))
    if req_get.get('name_product'):
        queryset = queryset.filter(title__icontains=req_get.get('name_product'))
    if req_get.get('seller'):
        queryset = queryset.filter(catalog__seller__title__iexact=req_get.get('seller'))
    if req_get.get('in_stock') == 'on':
        queryset = queryset.filter(catalog__count=True)
    return queryset


def query_sorted(request, queryset):
    """
    Метод сортировки товаров: по цене, по кол-ву отзывов, по популярности, по новизне
    :param request:
    :param queryset:
    :return:
    """

    sort_dict = {
        'price': '-avg_price',
        'rev_price': 'avg_price',
        'review': '-count_review',
        'rev_review': 'count_review',
        'new': '-created_at',
        'rev_new': 'created_at',
        'popular': '-view_count',
        'rev_popular': 'view_count',
    }

    queryset = queryset.order_by(sort_dict.get(request.GET.get('sorted')))
    return queryset


def query_sale(queryset):
    for good in queryset:
        if good.discount and good.discount.active:
            good.discounted_price = SaleService.calculate_sale(good.avg_price, good.discount)
            good.sale = SaleService.get_percent_from_old_price(good.avg_price, good.discounted_price)
    return queryset


def query_sale_annotate(queryset):
    queryset = queryset.annotate(discounted_price=Case(
        When(discount__variants__title='Percent',
             then=F('avg_price') - F('avg_price') * F('discount__size') / 100),
        When(discount__variants__title='Sum',
             then=Case(When(discount__size__lt=F('avg_price'),
                            then=F('avg_price') - F('discount__size')), default=1, output_field=DecimalField())),
        When(discount__variants__title='Fixed',
             then=F('discount__size')), output_field=DecimalField()),
        sale=100 - F('discounted_price') / F('avg_price') * 100)
    return queryset


def query_sale_annotate_slim(queryset):
    sale_goods = queryset.filter(discount__closed_at__gte=datetime.datetime.now())
    percent_sale = sale_goods.filter(discount__variants__title='Percent')
    sum_sale = sale_goods.filter(discount__variants__title='Sum')
    fixed_sale = sale_goods.filter(discount__variants__title='Fixed')

    percent_sale = percent_sale.annotate(
        discounted_price=F('avg_price') - F('avg_price') * F('discount__size') / 100)
    sum_sale = sum_sale.annotate(
        calculate_sale=F('avg_price') - F('discount__size'),
        discounted_price=Case(When(calculate_sale__gt=0, then=F('calculate_sale')), default=1))
    fixed_sale = fixed_sale.annotate(discounted_price=F('discount__size'))

    non_sale_goods = queryset.filter(discount__closed_at__lt=datetime.datetime.now())

    sale_goods = percent_sale & sum_sale & fixed_sale & non_sale_goods

    sale_goods = sale_goods.annotate(
        discounted_price=Case(When(discount__active=True, then=F('discounted_price')),
                              default='avg_price', output_field=DecimalField()),
        sale=100 - F('discounted_price') / F('avg_price') * 100)

    return sale_goods
