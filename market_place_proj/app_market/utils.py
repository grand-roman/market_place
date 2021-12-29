import json
import pickle
import random
from typing import Any, Dict, Iterable, List, Optional, Union

from django.core.cache import cache
from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import get_language

import pika
from app_market.models import (
    Cart,
    CartSale,
    Catalog,
    Category,
    Discount,
    GetKey,
    Good,
    GoodView,
    Order,
    RelatedGoodGroup,
)

from market_place_proj.constants import CacheTime, CounterSettings
from market_place_proj.settings import DELIVERY_CONDITION, DELIVERY_MAX, DELIVERY_MIN, DELIVERY_ZERO, RMQ_HOST


class CompareService:
    """
    Сервис сравнения товаров на основе кэша

    Методы:
    get_compare_ids: получение всех идентификаторов товаров в сравнении
    compare: запускает сравнение
    count: возвращает количество товаров в сравнениях
    """

    @classmethod
    def get_compare_ids(cls, request: HttpRequest) -> List[int]:
        """
        Метод получает все идентификаторы товаров в сравнении.
        Используется в списке товаров для показа кнопки в двух состояниях:
        - добавить товар в сравнение, - удалить товар из сравнения

        return: список идентификаторов
        """
        data = cache.get(GetKey.compare_key(request))
        result = list()
        if data:
            category_list = data.get('categories', list())
            for cat in category_list:
                goods = data.get(cat.pk)
                if not goods:
                    continue
                for good in goods:
                    result.append(good.pk)
        return result

    @classmethod
    def compare(cls, compare_list: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Метод выполняет сравнение товаров в категории

        arguments:
        compare_list: входящий список товаров для сравнения
        return: Словарь товаров
        """
        if not compare_list:
            return
        result = dict()
        good = list()
        prices = list()
        rates = list()
        # перечисляем записи в queryset
        for col, data in enumerate(compare_list):
            # запомним названия
            good.append(dict(title=data.title, image=data.image, pk=data.pk, category_pk=data.category.pk))
            # запомним цены
            prices.append(dict(title=data.title, price=data.price, price_with_discount=data.price))
            # запомним рейтинги
            rates.append(dict(title=data.title, yellow=3, gray=2))
            # и пройдемся по свойствам и заполним сводную таблицу свойств
            for key, value in json.loads(data.description):
                values = result.get(key, [dict(title=data.title, value=None) for _ in range(len(compare_list))])
                values[col] = dict(title=data.title, value=value)
                result[key] = values
        # перемесим свойства
        new_result = list()
        for key, values in result.items():
            unique = True
            unique_values = set()
            for item in values:
                if not item['value']:
                    unique = True
                    continue
                unique_values.add(item['value'].lower())
            if not len(unique_values) == len(values):
                unique = False
            new_result.append(dict(row=key, unicue=unique, values=values))
        return dict(goods=good, prices=prices, rates=rates, props=new_result)

    @classmethod
    def count(cls, request: HttpRequest) -> Dict[str, int]:
        """
        выдаёт количество товаров в сравнениях
        """
        data = cache.get(GetKey.compare_key(request), dict())
        return data.get('count', 0)


class SaleService:

    @classmethod
    def calculate_sale(cls, price, discount):
        variants = {'Percent': cls.get_percent, 'Sum': cls.get_sum, 'Fixed': cls.get_fixed}
        return variants[discount.variants.title](price, discount.size)

    @classmethod
    def get_percent(cls, price, discount):
        return price - price * discount / 100

    @classmethod
    def get_sum(cls, price, discount):
        discounted_price = price - discount
        return discounted_price if discounted_price > 0 else 1

    @classmethod
    def get_fixed(cls, price, discount):
        return discount

    @classmethod
    def get_percent_from_old_price(cls, old_price, discounted_price):
        return round(100 - discounted_price / old_price * 100)


def get_related_group_sale(queryset):
    """метод получения приоритетной скидки на набор товаров"""
    for group in RelatedGoodGroup.objects.all().order_by('discount__weight'):
        good1 = queryset.filter(good__group__code=group.group1.code).first()
        good2 = queryset.filter(good__group__code=group.group2.code).first()
        if good1 and good2:
            queryset.group = (good1.good, good2.good)
            return group.discount


def get_cart_sale(queryset):
    """метод получения приоритетной скидки на корзину"""
    total_price = queryset.aggregate(total_price=Sum('catalog__price'))['total_price']
    if total_price:
        cart_sales = CartSale.objects.filter(Q(quantity=len(queryset)) & Q(total_price__lte=total_price)).values(
            'discount__pk').order_by('-discount__weight').first()
        cart_sale_pk = cart_sales['discount__pk'] if cart_sales else None
        if cart_sale_pk:
            cart_sale = Discount.objects.get(pk=cart_sale_pk)
            return cart_sale


def get_cart_sales(queryset):
    """получения приоритетной скидки на корзину или на набор товаров"""
    queryset.group = None
    cart_sale = list(filter(None, [get_cart_sale(queryset), get_related_group_sale(queryset)]))
    if cart_sale:
        discount = Discount.objects.filter(pk__in=[sale.pk for sale in cart_sale]).order_by('-weight').first()
        discount = [sale for sale in cart_sale if sale.pk == discount.pk][0]
        # фиксирование скидки на набор товаров в аннотации если такой есть
        if queryset.group:
            queryset = queryset.annotate(group_discount=Case(
                When(good__pk__in=[good.pk for good in queryset.group], then=Value(discount.pk)),
                output_field=IntegerField(), default=None)).order_by('-group_discount')
        # иначе скидка на корзину
        else:
            # запись скидки на корзину
            Cart.objects.all().update(cart_discount=discount)
            # cart_sale_annotate(queryset, discount)
        return queryset
    return None


def get_goods_sale_by_priority(queryset):
    """получение скидок на каждый товар"""
    for good in queryset:
        sellers_discounts = [good.discount for good in Catalog.objects.filter(good__pk=good.pk)]
        discounts = filter(None, [good.good.discount, good.good.category.discount, *sellers_discounts])
        good.discount = sorted(list(iter(discounts)), key=lambda discount: discount.weight, reverse=True)[0]
        good.discounted_price = SaleService.calculate_sale(good.catalog.price, good.discount)
    return queryset


class SaleCartService:
    @classmethod
    def get_sale(cls, queryset):
        """главный метод получения итоговой скидки"""
        # первичная инициализация значений: заполнение пустых цен каталогов для корректной работы скидок
        queryset = queryset.annotate(discounted_price=Sum(0), group_discount=Sum(0))
        cart_discounts = get_cart_sales(queryset)
        # если скидки на корзину или на набор товаров есть, то отмечаем их в аннотации
        if cart_discounts:
            queryset = cart_discounts
        # иначе вычисление скидки на каждый товар по отдельности
        else:
            discounted_goods = queryset.select_related('good__discount', 'good__category__discount').filter(
                Q(good__discount__isnull=False) | Q(good__category__discount__isnull=False))
            queryset = get_goods_sale_by_priority(discounted_goods)
        return queryset

    @classmethod
    def get_discounted_total_price(cls, queryset, total_price):
        """вычисление итоговой цены со скидкой на основе queryset модели Cart"""
        cart_sale = queryset.values_list('cart_discount').first()[0]
        group_sale = queryset.values_list('group_discount').first()[0]
        queryset.group_total_price = {}
        # вычисление итоговой цены со скидкой на корзину
        if cart_sale:
            discount = Discount.objects.get(pk=cart_sale)
            discounted_total_price = SaleService.calculate_sale(total_price, discount)
        # вычисление итоговой цены со скидкой на набор тоавров
        elif group_sale:
            group = queryset.filter(group_discount__isnull=False)
            group_total_price = sum(good.catalog.price for good in group)
            group_discount = SaleService.calculate_sale(group_total_price, Discount.objects.get(pk=group_sale))
            discounted_total_price = total_price - group_total_price + group_discount
            # запись исходной цены на набор товаров и цены на набор с учетом скидки
            queryset.group_total_price = {'group_total_price': group_total_price, 'group_discount': group_discount}
        # иначе вычисление итоговой цены с учетом скидки на каждый товар по отдельности
        else:
            total_summ = 0
            discounted_total_summ = 0
            for good in queryset:
                total_summ += good.catalog.price * good.count
                discounted_total_summ += good.discounted_price * good.count
            discounted_total_price = total_price - total_summ + discounted_total_summ
        return discounted_total_price


class CartService:
    """
    Сервис корзины

    методы:
    get_good_from_cart: получает 1 товар из корзины для операций.
    add_good_to_cart: добавляет товар случайного или конкретного продавца в корзину
    change_good_count_in_cart - изменяет количество товара в позиции корзины
    delete_good_from_cart: удаляет товар из корзины
    get_goods_from_cart: получает все товары корзины
    update_good_in_cart: обновляет позицию товара в корзине. количество, продавец
    get_header_info: возвращает количество товара в корзине и цену корзины для header
    calculate_amount_for_all_goods_in_cart: рассчитывает стоимость корзины для оплаты
    clear: выполняет жесткую очистку модели
    get_unique_seller_count: получает уникальный список продавцов для товара
    delete_cache: очищает закешированную иконку корзины в header
    calculate_sale_price: расчитывает цену покупки товара в зависимости от наличия скидки
    _check_goods_count: внутренний метод проверяет наличие у продавца достаточного количества товара
    перед модификацией
    _update_goods_count: внутренний метод изменяет количество товаров в корзине
    _add_good_to_cart: внутренний метод выполняет непосредствено добавление товара
    """

    @classmethod
    def get_good_from_cart(cls, request: HttpRequest, new_good: Union[Catalog, Good]) -> Optional[QuerySet]:
        """
        метод получает из корзины товар, который нужно модифицировать

        аргументы:
        new_good: товар из каталога для модификации. М.б. объектом модели Good и Catalog

        return: queryset
        """

        def filter_by_user(qs: QuerySet) -> QuerySet:
            """
            подфункция возвращает набор данных для юзера или для анонимного юзера
            """
            if request.user.is_authenticated:
                qs = qs.filter(user=request.user)
            else:
                qs = qs.filter(anon_user=GetKey.anonymous_key(request))
            return qs

        # достанем товары в зависимости от того, что пришло: каталог или товар
        if isinstance(new_good, Catalog):
            goods = Cart.objects.filter(catalog=new_good, soft_delete=False)
            goods = filter_by_user(goods)
        else:
            goods_qs = [g.id for g in new_good.catalog.all()]
            goods = Cart.objects.filter(catalog_id__in=goods_qs, soft_delete=False)
            goods = filter_by_user(goods)

        goods = goods.select_related('good', 'user', 'catalog', 'catalog__seller', 'catalog__good')
        if goods.count() > 0:
            return goods

    @classmethod
    def add_good_to_cart(cls, request: HttpRequest, new_good: Union[Good, Catalog], count: int = 1) -> None:
        """
        метод добавляет случайный товар в корзину

        аргументы:
        new_good: товар из каталога для модификации. М.б. объектом модели Good и Catalog
        count: количество товара для добавления. по умолчанию 1
        """
        cls.delete_cache(request)
        # проверим наличие этого товара в корзине
        goods = cls.get_good_from_cart(request, new_good)
        # и увеличим количество товара в корзине
        if goods:
            # проверим, достаточно ли товара
            cls._check_goods_count(goods, count)
            cls._update_goods_count(goods, count)
            return
        # Теперь можно запросить товар для добавления в корзину
        cls._add_good_to_cart(new_good, count, request)

    @classmethod
    def delete_good_from_cart(cls, request: HttpRequest, good_id: int) -> None:
        """
        метод удаляет конкретный товар из корзины

        аргументы:
        good_id: идентификатор позиции модели Cart
        """
        cls.delete_cache(request)
        Cart.objects.filter(id=good_id).delete()

    @classmethod
    def change_good_count_in_cart(cls, good: Catalog, count: int) -> Optional[bool]:
        """
        метод устанавливает новое количество товара у позиции корзины

        аргументы:
        good: объект модели Catalog, который нужно обновить
        count: новое количество, которое нужно установить
        """
        object = Cart.objects.get(catalog=good)
        if not object:
            raise Http404(f'{good} отсутствует в корзине')
        if object.count + count > good.count:
            raise Http404(
                'Количество товара в корзине {} превышает количество товара в магазине {}'.format(
                    object.count + count,
                    good.count
                ))
        if object.count + count < 1:
            Cart.objects.filter(catalog=good).delete()
            return True
        Cart.objects.filter(catalog=good).update(count=F('count') + count)
        return True

    @classmethod
    def get_goods_from_cart(cls, request: HttpRequest = None,
                            user_id: int = None):
        """метод возвращает queryset с товарами корины конкретного пользователя
        аргументы:
        request
        user_id: идентификатор пользователя
        идентификация пользователя происходит или по id или по request.user
        """
        qs = Cart.objects.filter(soft_delete=False)
        # отфильтруем товар в зависимости от входных данных
        if request:
            if request.user.is_authenticated:
                qs = qs.filter(user=request.user)
            else:
                qs = qs.filter(anon_user=GetKey.anonymous_key(request))
        elif user_id:
            qs = qs.filter(user_id=user_id)
        qs = qs.select_related('user', 'good', 'good__image', 'good__group', 'good__category',
                               'catalog', 'catalog__seller', 'catalog__good', 'catalog__good__image',
                               'good__discount__variants', 'catalog__discount__variants',
                               'catalog__good__category__discount__variants',
                               'catalog__good__group')

        qs = DiscountService.update_queryset(qs, 'cart')
        total_sale_price, \
        total_price, \
        total_count = CartService.calculate_amount_for_all_goods_in_cart(qs)
        cart_discount_dict = DiscountService._get_cart_discount(total_price, total_count)
        has_cart_discount, size, variant = False, 0, ''
        if cart_discount_dict:
            qs = DiscountService._apply_cart_discount(qs)
            total_sale_price = DiscountService._calculate_discount_price(
                total_price,
                cart_discount_dict.get('discount__variants__title'),
                cart_discount_dict.get('discount__size'))
            has_cart_discount = True
            size = cart_discount_dict.get('discount__size')
            variant = cart_discount_dict.get('discount__variants__title')
        return qs, dict(discounted_total_price=total_sale_price,
                        total_price=total_price, total_count=total_count,
                        has_cart_discount=has_cart_discount,
                        variant=variant,
                        size=size,
                        )

    @classmethod
    def update_good_in_cart(cls, **kwargs) -> None:
        """
        Метод обновляет позицию в корзине. Изменяет продавца и/или количество

        аргументы:
        kwargs: словарь с ключами:
        catalog -- id записи в модели Catalog
        count -- количество товара
        instance_id -- id позиции в корзине (модель Cart)
        """
        # выйдем если в значениях пустота
        if kwargs.get('catalog') is None or kwargs.get('count') is None or kwargs.get('instance_id') is None:
            return
        good = Cart.objects.get(pk=kwargs['instance_id'])
        modify = False
        if good:
            count = kwargs.get('count')
            if count and good.count != count:
                good.count = count
                modify = True
            catalog = Catalog.objects.get(pk=kwargs.get('catalog'))
            if catalog and good.catalog != catalog:
                good.catalog = catalog
                modify = True
            if modify:
                good.save()

    @classmethod
    def get_header_info(cls, request: HttpRequest) -> Dict[str, Union[int, str]]:
        """
        метод возвращает количество товара в корзине и полную стоимость корзины для header
        return: словарь с ключами
        -- count - количество
        -- price - цена
        -- lang - язык
        """
        key = GetKey.cart_count_key(request)
        data = cache.get(key)
        if not data:
            qs, cart_amount_dict = CartService.get_goods_from_cart(request)
            lang = get_language().lower()
            data = dict(count=cart_amount_dict.get('total_count'),
                        price=cart_amount_dict.get('discounted_total_price'),
                        lang=lang)
            cache.set(key, data, timeout=60 * 60 * 24)
        return data

    @classmethod
    def calculate_amount_for_all_goods_in_cart(cls, queryset: QuerySet) -> Iterable[int]:
        """Метод вычисляет полную стоимость корзины на основе queryset модели Cart с учетом всех скидок
        return:
        - discounted_total_price - цена корзины со скидкой
        - total_price - цена корзины
        - total_count - количество товаров в корзине
        """
        total_sale_price = 0
        total_price_without_discount = 0
        total_with_discount = 0
        for item in queryset:
            total_sale_price += item.sale_price
            if item.total_price_with_discount:
                total_with_discount += 1
            if item.total_price_without_discount:
                total_price_without_discount += item.total_price_without_discount
        total_count = sum(item.count for item in queryset)
        return total_sale_price, total_price_without_discount, total_count

    @classmethod
    def clear(cls, request: HttpRequest) -> None:
        """метод очищает корзину конкретного пользователя"""
        if request.user.is_authenticated:
            Cart.objects.filter(user=request.user).delete()
        else:
            Cart.objects.filter(anon_user=GetKey.anonymous_key(request)).delete()

    @classmethod
    def get_unique_seller_count(cls, queryset: QuerySet) -> int:
        """метод возвращает количество уникальных продавцов"""
        return queryset.values_list('catalog__seller_id', flat=True).distinct().count()

    @classmethod
    def delete_cache(cls, request: HttpRequest) -> None:
        """
        Метод реализует сброс кэша корзины
        """
        cache.delete(GetKey.cart_key(request))
        cache.delete(GetKey.cart_count_key(request))

    @classmethod
    def calculate_sale_price(cls, queryset: QuerySet) -> QuerySet:
        """
        метод получает queryset корзины и рассчитывает стоимость товара со скидкой с учетом количества
        Вычисленное значение навешивается на метод класса
        Применяется строго после DiscountService.update_queryset()
        """
        for item in queryset:
            if item.price_with_discount:
                item.total_price_with_discount = item.price_with_discount * item.count
            else:
                item.total_price_with_discount = None
            if item.price_without_discount:
                item.total_price_without_discount = item.price_without_discount * item.count
            else:
                item.total_price_without_discount = None
            if item.total_price_with_discount:
                item.sale_price = item.total_price_with_discount
            else:
                item.sale_price = item.total_price_without_discount
            if not item.sale_price:
                item.sale_price = item.catalog.price * item.count
                item.total_price_without_discount = item.sale_price
        return queryset

    @classmethod
    def _check_goods_count(cls, goods: QuerySet, count: int) -> None:
        """
        Метод проверяет наличие товара в годном количестве и вызывает исключение в случае проблем

        аргументы:
        goods: QuerySet - набор товаров для проверки
        count: проверяемое количество товара
        return: raise Http404
        """
        exist_good_count = sum([g.catalog.count for g in goods])
        total_count = sum([g.count for g in goods]) + count
        if total_count > exist_good_count:
            raise Http404(
                f'У продавцов в вашей корзине недостаточно товаров {exist_good_count} для вашей покупки {total_count}')

    @classmethod
    def _update_goods_count(cls, goods: QuerySet, count: int) -> None:
        """
        метод обновляет количество товаров в корзине

        аргументы:
        goods: QuerySet позиций корзины
        count: новое количество товара к позиции корзины
        """
        for good in goods:
            if good.count + count <= good.catalog.count:
                good.count += count
                good.save()
                break
            else:
                add_count = good.catalog.count - good.count
                good.count += add_count
                count -= add_count
                good.save()

    @classmethod
    def _add_good_to_cart(cls, new_good: Union[Good, Catalog], count: int, request: HttpRequest) -> None:
        """
         метод добавляет товар в корзину

         аргументы:
         new_good: экземпляр модели Good или Catalog, который требуется добавить в корзину
         count: количество добавляемого товара
        """
        if isinstance(new_good, Good):
            good_for_cart = Catalog.objects.filter(
                Q(good__pk=new_good.pk) & Q(soft_delete=False) & Q(count__gte=count))
            if not good_for_cart:
                raise Http404('ни один магазин не сможет удовлетворить ваши потребности полностью')
            good_for_cart = random.choice(good_for_cart)
        else:
            good_for_cart = new_good
        good_in_cart = Cart()
        if request.user.is_authenticated:
            good_in_cart.user = request.user
        else:
            good_in_cart.anon_user = GetKey.anonymous_key(request)
        good_in_cart.catalog = good_for_cart
        good_in_cart.good = good_for_cart.good
        good_in_cart.count = count
        good_in_cart.save()


class GoodViewService:
    """
    Сервис просмотра товаров реализует сохранение истории просмотров

    методы:
    add_good_view: добавить товар в просмотренные
    """

    @classmethod
    def add_good_view(cls, request: HttpRequest, good_id: str) -> bool:
        """
        метод добавляет товар в историю просмотров
        количество товаров в просмотре регулируется константой CounterSettings.VIEW_COUNT
        больее которой объектов модели не создаётся
        Берётся самый старый товар и заменяется на новый

        аргументы:
        good_id: id товара модели Good

        return:
        True - если создали новый просмотр
        False - если что-то пошло не так
        """
        if not request.user.is_authenticated:
            return False
        view_key = GetKey.views_key(request)
        cache.delete(view_key)
        good = get_object_or_404(Good, id=good_id)
        goods = GoodView.objects.filter(user=request.user).order_by('-updated_at')
        if len(goods) < CounterSettings.VIEW_COUNT:
            obj, created = GoodView.objects.update_or_create(user=request.user, good=good)
            if obj or created:
                return True
        else:
            goods[len(goods) - 1].good = good
            goods[len(goods) - 1].save()
            return True

    @classmethod
    def del_good_view(cls, request: HttpRequest, good_id: int) -> None:
        """
        метод удаляет товар из просмотров

        агрументы:
        good_id - идентификатор товара в модели просмотров GoodView
        """
        GoodView.objects.filter(user=request.user, pk=good_id).delete()

    @classmethod
    def check_good_view(cls, request: HttpRequest, good_id: int) -> QuerySet:
        """
        метод проверяет наличие товара

        агрументы:
        good_id - идентификатор товара в модели просмотров GoodView
        """
        return GoodView.objects.filter(user=request.user, pk=good_id).exists()

    @classmethod
    def get_good_view_list(cls, request: HttpRequest, count: int = CounterSettings.VIEW_COUNT) -> QuerySet:
        """
        метод запрашивает список просмотренных товаров

        аргументы:
        count: количество товара (обычно максимум)

        return:
        QuerySet модели GoodView
        """
        if count > CounterSettings.VIEW_COUNT:
            count = CounterSettings.VIEW_COUNT
        elif count < 1:
            count = 1
        qs = GoodView.objects.filter(user=request.user).select_related(
            'user', 'good', 'good__image',
            'good__category').prefetch_related(
            'good__catalog').order_by('-updated_at')
        qs = qs.annotate(avg_price=Avg('good__catalog__price'))
        return qs[:count]

    @classmethod
    def get_good_view_count(cls, request: HttpRequest) -> int:
        """        запрос количества просмотров        """
        return GoodView.objects.filter(user=request.user).count()


class PayOrderService:
    """
    Сервис интеграции с сервисом оплаты

    методы:
    pay_order: оплатить заказ по идентификатору
    get_card_amount: получить стоимость товара в карзине и его количество
    get_order_by_id: получить объект заказа (модель Order) по идентификатору
    get_delivery_price: рассчитать стоимость доставки
    _send_message: внутренний метод отправляет заказ в сервис по оплате посредством шины RabbitMQ
    check_order: проверяет статус заказа - оплачено/неоплачено
    """

    @classmethod
    def pay_order(cls, order_id: int) -> None:
        """
        метод получает заказ по идентификатору и отправляет его в сервис оплаты

        аргументы:
        order_id: идентификатор заказа модели Order
        """
        order = cls.get_order_by_id(order_id)
        cls._send_message(order.response)

    @classmethod
    def get_card_amount(cls, user_id) -> Iterable[int]:
        """
        метод получает стоимость корзины дл формирования цены заказа

        аргументы:
        user_id: идентификатор авторизованного юзера

        return:
        цена корзины со всеми скидками, полная цена без скидок, полное количество товара
        """
        goods, cart_amount_dict = CartService.get_goods_from_cart(user_id=user_id)
        return cart_amount_dict.get('discounted_total_price'), \
               cart_amount_dict.get('total_price'), cart_amount_dict.get('total_count')

    @classmethod
    def get_order_by_id(cls, order_id):
        """метод возвращает экземпляр модели Order по идентификатору"""
        return Order.objects.prefetch_related(
            'detail').filter(
            id=order_id).annotate(
            price=ExpressionWrapper(
                Sum(F('detail__price') * F('detail__count')) + F('delivery_price'),
                output_field=DecimalField())).first()

    @classmethod
    def get_delivery_price(cls, delivery: str, price: float, sellers_count: int) -> int:
        """
        метод рассчитывает стоимость доставки в зависимости от цены и количества продавцов

        аргументы:
        delivery: тип доставки: express/ordinary
        price: цена заказа
        sellers_count: количество уникальных продавцов в заказе

        return:
        цена доставки
        """
        if delivery == 'express':
            return DELIVERY_MAX
        elif delivery == 'ordinary':
            if price < DELIVERY_CONDITION:
                return DELIVERY_MIN
            elif sellers_count > 1:
                return DELIVERY_MIN
            elif sellers_count == 1 and price >= DELIVERY_CONDITION:
                return DELIVERY_ZERO
        return 0

    @classmethod
    def check_order(cls, order: Order):
        """
        метод возвращает статус заказа

        аргумент:
        order: экземпляр модели заказа Order

        return:
        - True - если заказ оплачен
        - словарь если оплата не состоялась
        """
        if order.status == 'pay_success':
            return True
        else:
            return json.loads(order.status)

    @classmethod
    def _send_message(cls, data: Dict[Any, Any]) -> None:
        """
        внутренний метод ставит отплату в очередь rabbitMQ

        аргументы:
        data - данные, необходимые сервису оплаты
        """
        conn_params = pika.ConnectionParameters(RMQ_HOST)
        connection = pika.BlockingConnection(conn_params)
        channel = connection.channel()
        channel.queue_declare(queue='payment')
        channel.basic_publish(exchange='',
                              routing_key='payment',
                              body=pickle.dumps(data))
        connection.close()


class MainPageService:
    """
    Сервис разделов главной страницы сайта

    методы:
    get_limit_edtion_goods: получить набор товаров ограниченной серии
    get_hot_offers_goods: получить набор товаров горячих предложений
    get_categories_and_min_prices: получить набор категорий с минимальными ценами
    """

    @classmethod
    def get_limit_edtion_goods(cls) -> Optional[QuerySet]:
        """
        метод возвращает набор товаров модели Good ограниченной серии для главной страницы
         и кэширует их на определенное время

        return:
        None - если таких товаров нет
        QuerySet из Good - если что-то да нашлось
        """
        limit_edition = cache.get(GetKey.limit_edition_key())
        if not limit_edition:
            goods = Good.objects.filter(
                Q(short_list=True) & (Q(image__file__isnull=False) | Q(image__link__isnull=False))). \
                values_list('id', flat=True)
            if not goods or len(goods) < 2:
                return
            goods = cls._get_goods_by_id(goods, CounterSettings.LIMIT_EDITION_COUNT)
            limit_edition = dict(limit_good=goods[0], limit_goods=goods[1:])
        cache.set(GetKey.limit_edition_key(), limit_edition, CacheTime.LIMIT_EDITION)
        return limit_edition

    @classmethod
    def get_hot_offers_goods(cls) -> Optional[QuerySet]:
        """
        метод возвращает товары модели Good ограниченной серии для главной страницы

        return:
        None - если таких товаров нет
        QuerySet из Good - если что-то да нашлось
        """
        hot_offers = cache.get(GetKey.hot_offers_key())
        if not hot_offers:
            goods = Good.objects.filter(
                Q(discount__isnull=False) & (Q(image__file__isnull=False) | Q(image__link__isnull=False))).values_list(
                'id', flat=True)
            if not goods:
                return
            random.shuffle(list(goods))
            goods = cls._get_goods_by_id(goods, CounterSettings.LIMIT_HOT_GOOD_COUNT)
            hot_offers = dict(hot_offers=goods)
        cache.set(GetKey.hot_offers_key(), hot_offers, CacheTime.LIMIT_EDITION)
        return hot_offers

    @classmethod
    def get_categories_and_min_prices(cls) -> Dict[str, Any]:
        """
        метод получает категории с минимальными ценами и кеширует их на время

        return:
        словарь с лучшими категорими
        """
        result = []
        best_cats = cache.get(GetKey.best_cats_key())
        if not best_cats:
            ids = list(Category.objects.filter(level=1).values_list('id', flat=True))
            random.shuffle(ids)
            count = 0
            for id in ids:
                if count == CounterSettings.BEST_CATEGORY_COUNT:
                    break
                good = Good.objects.select_related('category', 'image')
                good = good.prefetch_related('catalog')
                good = good.filter(Q(category__id=id) & (Q(image__file__isnull=False) | Q(image__link__isnull=False)))
                good = good.annotate(avg_price=Avg('catalog__price')).order_by('avg_price').first()
                if good:
                    count += 1
                    result.append(good)
            best_cats = dict(best_cats=result)
            cache.set(GetKey.best_cats_key(), best_cats, CacheTime.CATEGORY_MIN_PRICE)
        return best_cats

    @classmethod
    def _get_goods_by_id(cls, ids: List[int], limit: int) -> QuerySet:
        """
        внутренний метод возвращает товары по идентификаторам
        перед выполнением запроса идентификаторы перемешиваются

        аргументы:
        ids: список идентификаторов
        limit: ограничение по количеству запрашиваемых идентификаторов

        return:
        QuerySet из Good
        """
        random.shuffle(list(ids))
        goods = Good.objects.select_related(
            'image', 'discount', 'discount__variants', 'category').annotate(
            avg_price=Avg('catalog__price'),
            count_review=Count('review')).filter(id__in=ids[:limit])
        return goods


class DiscountService:
    """сервис скидок для товаров
    Вкратце - на вход получаем queryset, в котором уже выполнены все select_related
    хотя возможно стоит делать это внутри сервиса, в зависимости от набора
    из полученного QS извлекаются значения в словарь.
    каждая строка может содержать скидки разной категории, поэтому сначала
    приводим ключи словаря к унифицированному виду, который не зависит от модели,
    затем выдираем приоритетную скидку,
    затем рассчитываем скидку и модифицируем запись исходного qs
    возвращаем qs

    методы:
    update_queryset: навешивает дополнительные данные по ценам, скидкам на свойства класса
    """

    @classmethod
    def update_queryset(cls, queryset: QuerySet, model: str) -> QuerySet:
        """
        метод добавляет скидки на товар к queryset через запись в новые свойства.
        Новые свойства нельзя использовать в привычных операциях с queryset

        аргументы:
        queryset: набор товаров, для которых надо рассчитать скидки
        model: явное указание модели для расчета скидок (cart)
        в настоящее время реализован расчет для модели Cart
        Вы можете расширить функционал метода расчетом для моделей
        Good Catalog перенастроив словарь keys, который запрашивает данные для скидок из моделей

        основные этапы:
        - получить все значения модели в список
        - получить приоритетные скидки для товаров (в словарь, где ключ - идентификатор товара)
        - получить скидки для наборов group (скидки на набор переписывают скидки на товар, категорию)
        - навесить скидку на каждый товар в queryset
        - расчитать цену покупки и также навесить её на свойство в queryset
        """
        if model == 'cart':
            keys = dict(id_id=F('id'), price=F('catalog__price'),
                        group_title=F('catalog__good__group__title'),
                        group_id=F('catalog__good__group__id'))
            keys.update(cls._get_keys('catalog__good__category__discount__', 'category'))
            keys.update(cls._get_keys('catalog__good__discount__', 'good'))
            keys.update(cls._get_keys('catalog__discount__', 'catalog'))
            values = list(queryset.values(**keys))
            discounts_dict = cls._get_priority_discount(values)
            groups_dict = cls._get_group_discount(values)
            if groups_dict:
                queryset = cls._apply_group_discounts_dict_to_queryset(groups_dict, queryset)
            queryset = cls._apply_discounts_dict_to_queryset(discounts_dict, queryset)
            queryset = CartService.calculate_sale_price(queryset)

        return queryset

    @classmethod
    def _get_keys(cls, prefix: str, fieldname: str) -> Dict[str, Any]:
        """
        метод получает ключи для запроса скидок из модели и переименует их
        в универсальные. не зависимо от входящей модели
        аргументы:
        fieldname: часть названия поля модели, которую нужно заменить на универсальную
        prefix: то, на что нужно заменить
        """
        result = dict()
        result[f'{fieldname}__title'] = F(prefix + 'variants__title')
        result[f'{fieldname}__weight'] = F(prefix + 'weight')
        result[f'{fieldname}__size'] = F(prefix + 'size')
        result[f'{fieldname}__active'] = F(prefix + 'active')
        result[f'{fieldname}__created_at'] = F(prefix + 'created_at')
        result[f'{fieldname}__closed_at'] = F(prefix + 'closed_at')
        result[f'{fieldname}__weight'] = F(prefix + 'weight')
        result[f'{fieldname}__soft_delete'] = F(prefix + 'soft_delete')
        return result

    @classmethod
    def _get_cart_discount(cls, total_price: int, total_count: int) -> Dict[str, any]:
        """
        метод реализует получение вариантов скидок на всю корзину товаров
        возвращается всегда 1 скидка

        аргументы:
        total_price: полная цена корзины
        total_count: количество товара в корзины

        return:
        словарь с данными скидки
        """
        now = timezone.now()
        cart_discount = CartSale.objects.select_related('discount__variants').filter(
            quantity__lte=total_count, total_price__lte=total_price, discount__active=True,
            discount__soft_delete=False,
            discount__created_at__lte=now, discount__closed_at__gte=now,
        ).order_by('discount__weight').values('discount__variants__title', 'discount__size').last()
        return cart_discount

    @classmethod
    def _apply_cart_discount(cls, queryset: QuerySet) -> QuerySet:
        """
        внутренний метод обнуляет предыдущие скидки на товар в queryset
        и пересчитывает цену покупки каждого товара
        для кааждого товара прописываются свойства
        discount_key
        discount_type
        group_discount
        чтобы в представлении было понятно, что за скидка у каждого товара

        return Queryset
        """
        for item in queryset:
            item.discount_key = 'cart'
            item.discount_type = 'Cart discount'
            item.discount_weight = None
            item.discount_size = None
            item.group_discount = 'Cart discount'

            item.discount_active = None
            item.discount_created_at = None
            item.discount_closed_at = None
            item.price_with_discount = None
        queryset = CartService.calculate_sale_price(queryset)
        return queryset

    @classmethod
    def _get_group_discount(cls, values) -> Optional[Dict[str, Any]]:
        """
        внутренний метод получает скидки для товаров из групп

        аргументы: values: словарь с данными о товаре и связанных с ними скидках

        groups_id - список всех идентификаторов групп, по которым запрашивать соотношения групп
        goods - словарь для сортировки товаров по идентификаторам групп.
        сортируем товары по группам, запрашиваем соотношения групп по groups_id
        достаём пары групп и комбинируем товары в наборы с расчетом скидки

        return:
        None если скидок нет
        словарь ключ - идентификатор позиции в корзине, значение - размер скидки
        """
        groups_id = [value.get('group_id') for value in values if value.get('group_id')]
        groups = cls._get_related_groups(groups_id)
        if not groups:
            return None
        resorted_goods = cls._resort_goods_by_group_id(values)
        good_with_discount = cls._get_discount_for_group(resorted_goods, groups)
        return good_with_discount if good_with_discount else None

    @classmethod
    def _get_related_groups(cls, groups_id: List[int]) -> QuerySet:
        """метод возвращает сет из пар групп, в которых id из списка groups_id"""
        groups = RelatedGoodGroup.objects.select_related('discount__variants').filter(
            Q(discount__soft_delete=False) & (Q(group1__id__in=groups_id) | Q(group2__id__in=groups_id))
        )
        return groups

    @classmethod
    def _resort_goods_by_group_id(cls, data: Iterable):
        """
        метод реализует перегруппировку словаря товаров по group_id
        return:
        словарь, где ключ - идентификатор группы, значение - список товаров в этой группе
        """
        result = dict()
        for value in data:
            key = value.get('group_id')
            if key:
                good_group_list = result.get(key, list())
                good_group_list.append(value)
                result[key] = good_group_list
        # пересортируем словарь результатов
        for key, value in result.items():
            value = sorted(value, key=lambda x: x['price'], reverse=True)
            result[key] = value
        return result

    @classmethod
    def _get_discount_for_group(cls, resorted_goods, groups: RelatedGoodGroup.objects):
        """
        метод реализует получение типа и размера скидок для каждого group_id в наборе

        аргументы:
        resorted_goods - словарь, ключ - идентификатор группы, значение - список товаров корзины
        в этой группе
        groups - экземпляр модели RelatedGoodGroup, которая устанавливает пары групп для наборов товаров

        return:
        словарь, где ключ - идентификатор позиции в корзине, значение - скидка для этой позиции

        как работает:
        проходим в цикле по наборам, выбираем из корзины соответствующие части наборов.
        Далее применим zip чтобы выбрать одинаковое количество наборов и добавим в результат скидку
        для каждого товара
        """
        result = dict()
        now = timezone.now()
        for group in groups:
            # пропустим протухшие скидки
            if not group.discount.active:
                continue
            elif not group.discount.created_at < now < group.discount.closed_at:
                continue
            left_set = resorted_goods.get(group.group1.id)
            right_set = resorted_goods.get(group.group2.id)
            if left_set and right_set:
                for left, right in zip(left_set, right_set):
                    result[left.get('id_id')] = group.discount
                    result[right.get('id_id')] = group.discount
        return result

    @classmethod
    def _get_priority_discount(cls, values):
        """метод перебирает словарь корзины и формирует словарь приоритетных скидок на товар"""
        result = dict()
        # перечислим все товары
        for item in values:
            # подберём максимальные скидки
            result[item['id_id']] = DiscountService._get_max_discount_for_good(item)
        # вернём их для модификации queryset
        return result

    @classmethod
    def _get_max_discount_for_good(cls, item):
        """метод достаёт скидку с максимальным весом"""
        discounts = []
        keys = ['category', 'good', 'title']
        now = timezone.now()
        for key in keys:
            # пропустим протухшие скидки
            if not item.get(f'{key}__active'):
                continue
            elif not item.get(f'{key}__created_at') < now < item.get(f'{key}__closed_at'):
                continue
            elif item.get(f'{key}__title'):
                value = [
                    item.get('id_id'),
                    key,
                    item.get(f'{key}__title'),
                    item.get(f'{key}__weight'),
                    item.get(f'{key}__size'),
                    item.get(f'{key}__active'),
                    item.get(f'{key}__created_at'),
                    item.get(f'{key}__closed_at'),
                    item.get('price'),
                ]
                discounts.append(value)
        if len(discounts) == 0:
            return None
        return max(discounts, key=lambda x: x[3])

    @classmethod
    def _apply_group_discounts_dict_to_queryset(cls, groups_dict: Dict[str, Any], queryset: QuerySet) -> QuerySet:
        """метод навешивает групповые скидки на каждый товар из queryset"""
        for item in queryset:
            discount = groups_dict.get(item.id)
            if not discount:
                continue
            item.discount_key = 'group'
            item.discount_type = discount.variants.title
            item.discount_weight = discount.weight
            item.discount_size = discount.size
            item.group_discount = \
                f'{item.good.group.id}:{item.discount_key}:{item.discount_type}:{item.discount_weight}:{item.discount_size}'
            item.discount_active = discount.active
            item.discount_created_at = discount.created_at
            item.discount_closed_at = discount.closed_at
            item.price_without_discount = item.catalog.price
            item.price_with_discount = cls._calculate_discount_price(
                item.price_without_discount, item.discount_type, item.discount_size) if discount else None
            if discount and item.price_with_discount >= item.price_without_discount:
                item.price_with_discount = None
        return queryset

    @classmethod
    def _apply_discounts_dict_to_queryset(cls, discounts_dict, queryset):
        """
        метод навешивает скидки на свойства queryset
        """
        for item in queryset:
            discount = discounts_dict.get(item.id)
            if hasattr(item, 'discount_key') and item.discount_key == 'group':
                continue
            item.discount_key = discount[1] if discount else None
            item.discount_type = discount[2] if discount else None
            item.discount_weight = discount[3] if discount else None
            item.discount_size = discount[4] if discount else None
            item.discount_active = discount[5] if discount else None
            item.discount_created_at = discount[6] if discount else None
            item.discount_closed_at = discount[7] if discount else None
            item.price_without_discount = discount[8] if discount else None
            item.price_with_discount = cls._calculate_discount_price(
                item.price_without_discount, item.discount_type, item.discount_size
            ) if discount else None
            # обнулим скидку, если цена с ней больше чем исходная цена
            if discount and item.price_with_discount >= item.price_without_discount:
                item.price_with_discount = None
            if discount:
                item.group_discount = f'Discount:{item.discount_key}:{item.discount_type}:{item.discount_size}'

        return queryset

    @classmethod
    def _calculate_discount_price(cls, price: float, discount_type: str, size: int) -> float:
        """метод раcсчитывает цену скидки

        аргументы:
        price: цена товара
        discount_type: тип скидки, Percent | Sum | Fixed
        size: размер скидки

        return:
        float - окончательная цена покупки
        """
        if discount_type == 'Percent':
            return price - price * size / 100
        elif discount_type == 'Sum':
            # итоговая стоимость товара не может быть менее одного рубля
            price = price - size
            return price if price > 1 else 1
        elif discount_type == 'Fixed':
            return size
