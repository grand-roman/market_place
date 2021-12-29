import datetime
import hashlib
import json
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.validators import MinValueValidator
from django.db.models import Avg, Max, Prefetch, Q, Sum
from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView, TemplateView, View
from django.views.generic.edit import FormMixin

from app_market.forms import AddGoodToCartWithCountForm, CartForm2, MessagesForm, OrderingForm, PayForm
from app_market.models import Catalog, Category, Discount, GetKey, Good, Order, OrderDetail, Review, Seller
from app_market.templatetags.goods_cards import query_sale_annotate
from app_market.utils import (
    CartService,
    CompareService,
    GoodViewService,
    MainPageService,
    PayOrderService,
    SaleService,
)
from app_users.forms import LoginForm
from view_breadcrumbs import BaseBreadcrumbMixin, DetailBreadcrumbMixin, ListBreadcrumbMixin

from market_place_proj.constants import CacheTime


class IndexView(TemplateView):
    """
    Временное представление для вывода индекса
    """
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        """метод пробрасывает дополнительные товары в главную страницу,
        а также запускает счетчик обратного отсчета"""
        context = super().get_context_data(**kwargs)
        limit_edition = MainPageService.get_limit_edtion_goods()
        if not limit_edition:
            return context
        context.update(limit_edition)
        hot_offers = MainPageService.get_hot_offers_goods()
        if not hot_offers:
            context['hot_offers'] = []
        else:
            context.update(hot_offers)
        best_cats = MainPageService.get_categories_and_min_prices()
        if not best_cats:
            context['best_cats'] = []
        else:
            context.update(best_cats)
        context['cutdown'] = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%d.%m.%Y 23:59')

        return context


class CategorySlugView(BaseBreadcrumbMixin, TemplateView):
    """
    Представление для вывода товаров по slag`у категории site.ru/catalog/category/<str:slug>/
    """
    template_name = 'app_market/category.html'

    @property
    def crumbs(self):
        category = cache.get(
            hashlib.md5(self.request.get_full_path().encode()).hexdigest())
        if category:
            category = category.first().category
        else:
            category = get_object_or_404(Category, slug=self.kwargs.get('slug'))
        return [
            (_('Catalog'), reverse_lazy('sellers_list')), (category.title, reverse_lazy('sellers_list'))
        ]

    def get_context_data(self, slug, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['slug'] = slug
        return context


class SellerListView(ListView):
    """
    представление для вывода списка продавцов
    """
    model = Seller
    context_object_name = 'sellers'
    template_name = 'app_market/seller_list.html'


class SellerView(DetailView):
    """
    Представление для вывода списка Товаров конкретного продавца
    """
    model = Seller
    context_object_name = 'seller'
    template_name = 'app_market/seller_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # пропишем пк тут, иначе с каждым вычислением идёт обращение в базу
        pk = self.kwargs.get('pk')
        # достанем id всех товаров, которые есть в сравнении
        ids = CompareService.get_compare_ids(self.request)
        context['ids'] = ids
        # достанем товары для продавца
        context['goods'] = Seller.objects.get(
            pk=pk).catalog.filter(popularity_index__gt=0).select_related(
            'good',
            'good__image',
            'good__category').order_by(
            'good__category__title',
            'good__good_type')[:20]
        self.request.session['compare_redirect'] = reverse('seller', kwargs=dict(pk=pk))
        return context


class GoodDetailView(BaseBreadcrumbMixin, DetailView):
    """
    Вьюшка для просмотра свойств товара.
    """
    model = Good
    template_name = 'app_market/product.html'

    @property
    def crumbs(self):
        current_object = self.object
        return [
            (_('Catalog'), reverse_lazy('catalog')),
            (current_object.category, reverse_lazy('category', kwargs={'slug': current_object.category.slug})),
            (current_object.title, '')
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        good = context.get('good')
        # Если покупатель заходит на детальную страницу товара, то этот
        # товар добавляется в его список последних просмотренных товаров.
        GoodViewService.add_good_view(self.request, good.id)
        # продолжаем вывод деталей
        context['avg_price'] = round(good.catalog.aggregate(avg_price=Avg('price')).get('avg_price'), 2)
        if good.discount and good.discount.active:
            context['discounted_price'] = SaleService.calculate_sale(context['avg_price'], good.discount)
            context['sale'] = SaleService.get_percent_from_old_price(context['avg_price'], context['discounted_price'])
        good.description = json.loads(good.description)
        # Добавим форму для добавления товара в корзину вместе с количеством
        form = AddGoodToCartWithCountForm(initial=dict(
            id=good.id,
            count=1,
            max_count=good.catalog.aggregate(max_count=Max('count')).get('max_count')))
        context['form'] = form
        return context

    def get_queryset(self, **kwargs):
        queryset = super(GoodDetailView, self).get_queryset().filter(soft_delete=False). \
            select_related('category', 'image', 'discount__variants'). \
            prefetch_related('catalog', 'catalog__seller', 'catalog__discount__variants', 'tag',
                             Prefetch("review", Review.objects.select_related('user', 'good').
                                      filter(soft_delete=False))).annotate(avg_price=Avg('catalog__price'))
        return queryset

    def get_object(self, queryset=None):
        obj = cache.get_or_set(
            key=f'detail_prod_obj-{self.kwargs.get("pk")}',
            default=get_object_or_404(self.get_queryset(), pk=self.kwargs.get('pk')),
            timeout=CacheTime.DETAIL_PRODUCT
        )
        obj.view_count += 1
        obj.save(update_fields=['view_count'])
        return obj

    def post(self, request, pk):
        review = request.POST.get('review')
        if review:
            self.get_queryset().filter(pk=pk).first().review.create(user_id=request.user.id, good_id=pk, text=review)
        return redirect(request.path)


class CompareView(View):
    """
    get - выполнить сравнение
    post - добавить товар в сравнение
    """

    def get(self, request):
        """
        Вывести сравнение
        """
        data = cache.get(GetKey.compare_key(request), dict())
        count = data.get('count', 0)
        category_list = data.get('categories', list()) if data else list()
        return render(request, 'app_market/compare.html', context=dict(category_list=category_list, count=count))

    def post(self, request, id: int):
        """
        Добавить товар в сравнение
        """
        good = Good.objects.filter(pk=id).annotate(price=Avg('catalog__price'))
        if not good:
            raise Http404
        good = good[0]
        category = good.category
        compare_key = GetKey.compare_key(request)
        # достанем данные из кэша
        data = cache.get(compare_key, dict())
        good_list = data.get(category.pk, [])
        category_list = data.get('categories', [])
        count = data.get('count', 0)
        # обновим словарь
        if category not in category_list:
            category_list.append(category)
        if good not in good_list:
            good_list.append(good)
            count += 1
            data['count'] = count
            data[category.pk] = good_list
            data['categories'] = category_list
            # обратно в кэш
            cache.set(compare_key, data, timeout=CacheTime.COMPARE_GOODS)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class ClearCompareView(View):
    """
    Вьюшка очищает сравнение товаров.
    Метод get - полностью
    Метод post - удаляет конкретный товар
    """

    def get(self, request):
        """
        Очистить всю корзину
        """
        compare_key = GetKey.compare_key(request)
        cache.delete(compare_key)
        return redirect(reverse('view_compare'))

    def post(self, request, id: int):
        """
        Удалить один товар из сравнения
        """
        good = Good.objects.filter(pk=id).annotate(price=Avg('catalog__price'))
        if not good:
            raise Http404
        good = good[0]
        category = good.category
        compare_key = GetKey.compare_key(request)
        # достанем данные из кэша
        data = cache.get(compare_key, dict())
        good_list = data.get(category.pk)
        if not good_list:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        category_list = data.get('categories', list())
        count = data.get('count', 0)
        # обновим словарь
        if good in good_list:
            good_list.remove(good)
            count -= 1
        # если в списке не осталось товаров, удалим категорию и её списко товаров из кэша
        if len(good_list) == 0:
            data.pop(category.pk)
            category_list.remove(category)
        else:
            data[category.pk] = good_list
        data['count'] = count
        data['categories'] = category_list
        # обратно в кэш
        cache.set(compare_key, data, timeout=CacheTime.COMPARE_GOODS)
        compare_redirect = request.session.get('compare_redirect')
        if compare_redirect:
            return redirect(compare_redirect + f'#good_id_{good.pk}')
        return redirect(reverse('index'))


class CompareGoodsView(View):
    """
    Сравнение товаров в конкретной категории
    """

    def get(self, request, id):
        compare_key = GetKey.compare_key(request)
        data = cache.get(compare_key)
        compare_list = data.get(id)
        if compare_list:
            category_list = data.get('categories')
            compare_list = CompareService.compare(compare_list)
            request.session['prior_page'] = ('compare', id)
            return render(request, 'app_market/compare.html', context=dict(compare_list=compare_list,
                                                                           category_list=category_list))
        return redirect(reverse('view_compare'))


class CartView(View):
    """ Представление корзины """

    def get(self, request):
        # получим instances модели Cart
        instances, catalog, cart_amount_dict = self.get_instanses(request)
        if not instances:
            return render(request, template_name='app_market/cart.html', context=dict())
        # заполним список форм
        formset = []
        for index, instance in enumerate(instances):
            form = self._get_form(index, instance, catalog=catalog)
            formset.append(form)
        context = dict(formset=formset,
                       total_price=cart_amount_dict.get('total_price'),
                       discounted_total_price=cart_amount_dict.get('discounted_total_price'),
                       total_count=cart_amount_dict.get('total_count'),
                       has_cart_discount=cart_amount_dict.get('has_cart_discount'),
                       variant=cart_amount_dict.get('variant'),
                       size=cart_amount_dict.get('size'),
                       )
        return render(request, template_name='app_market/cart.html', context=context)

    def post(self, request):
        formset = []
        # получим instances модели Cart
        instances, catalog, cart_amount_dict = self.get_instanses(request)
        if not instances:
            return render(request, template_name='app_market/cart.html', context=dict())
        post_index = int(request.POST.get('index', '-1'))
        for index, instance in enumerate(instances):
            if index == post_index:
                form = self._get_form(index, instance, post=request.POST, catalog=catalog)
                if form.is_valid():
                    CartService.update_good_in_cart(**form.cleaned_data)
                    cache.delete(GetKey.cart_count_key(request))
                    return redirect(reverse_lazy('cart'))
                else:
                    print('invalid')
                    print(form.errors)
            else:
                form = self._get_form(index, instance, catalog=catalog)
            formset.append(form)
        context = dict(formset=formset,
                       total_price=cart_amount_dict.get('total_price'),
                       discounted_total_price=cart_amount_dict.get('discounted_total_price'),
                       total_count=cart_amount_dict.get('total_count'),
                       has_cart_discount=cart_amount_dict.get('has_cart_discount'))
        return render(request, template_name='app_market/cart.html', context=context)

    def _get_form(self, index, instance, **kwargs):
        initial = dict(
            index=index,
            instance_id=instance.id,
            count=instance.count,
            good_id=instance.catalog.good.id,
            cat_id=instance.catalog.id,
            title=instance.catalog.good.title,
            price=instance.catalog.price,
            total_price=instance.total_price_without_discount,
            discounted_price=instance.total_price_with_discount,
        )
        if instance.price_with_discount:
            initial['discounted_total_price'] = instance.price_with_discount * instance.count
        initial['group_discount'] = instance.group_discount if hasattr(instance, 'group_discount') else None
        if instance.catalog.good.image:
            if instance.catalog.good.image.file:
                initial['image'] = instance.catalog.good.image.file.url
            elif instance.catalog.good.image.link:
                initial['image'] = instance.catalog.good.image.link
        post_data = kwargs.get('post')
        if post_data:
            form = CartForm2(post_data, initial=initial)
        else:
            form = CartForm2(initial=initial)
        form.fields['count'].validators.append(
            MinValueValidator(limit_value=1,
                              message=_('Let there be at least 1 product'))
        )
        catalog = kwargs.get('catalog')
        filtered_catalog = [(c.id, c) for c in catalog if c.good.id == instance.catalog.good.id]
        initial_seller_id = self.get_initial_seller(filtered_catalog, instance)
        form.fields['catalog'].choices = filtered_catalog
        form.fields['catalog'].initial = initial_seller_id
        form.fields['catalog'].empty_label = None
        return form

    def get_instanses(self, request):
        """получим queryset для товаров в корзине"""
        instances, cart_amount_dict = CartService.get_goods_from_cart(request=request)
        if not instances:
            return None, None, None
        # запросим идентификаторы товаров для запроса их магазинов
        goods_ids = [instance.catalog.good.id for instance in instances]
        # запросим наличие товаров все сразу, чтобы не дёргать базу
        catalog = Catalog.objects.select_related('seller', 'good').filter(
            good_id__in=goods_ids, count__gt=0)
        return instances, catalog, cart_amount_dict

    def get_initial_seller(self, catalog_list, instance):
        """получаем идентификатор активного магазина в корзине"""
        for cat in catalog_list:
            if cat[1].id == instance.catalog.id:
                return cat[1].id


class GoodCartView(View):
    """
    вьюшка добавляет товары в корзину в зависимости от ситуации
    """

    def post(self, request: HttpRequest, mtd: str, good_id: int):
        count = int(request.POST.get('count', '1'))
        if mtd == 'add_random_good':
            # добавим товар случайного продавца из модели Good
            good = Good.objects.get(id=good_id)
            CartService.add_good_to_cart(request, good, count)
        elif mtd == 'add_good':
            # добавим товар конкретного продавца
            good = Catalog.objects.get(id=good_id)
            CartService.add_good_to_cart(request, good, count)
        elif mtd == 'delete_good':
            # удалим товар из корзины
            CartService.delete_good_from_cart(request, good_id)

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class ChangeGoodCountInCartView(View):
    """Представление для изменения количества товара"""

    def post(self, request: HttpRequest, mtd: str, good_id: int, count: int):
        if mtd == 'add':
            good = Catalog.objects.get(id=good_id)
            CartService.change_good_count_in_cart(good, count)
        elif mtd == 'remove':
            good = Catalog.objects.get(id=good_id)
            CartService.change_good_count_in_cart(good, (-1) * count)
        return HttpResponseRedirect(redirect(reverse_lazy('cart')))


class ViewedGoodListView(LoginRequiredMixin, ListBreadcrumbMixin, TemplateView):
    """
    представление показывает список просмотренных товаров
    """
    login_url = reverse_lazy('login')
    template_name = 'app_market/viewed_good_list.html'
    crumbs = [(_('Browsing history'), '')]


class ViewedProductsView(LoginRequiredMixin, View):
    """
    представление реализует операции add remove check count над просмотренными товарами
    """
    login_url = reverse_lazy('login')

    def post(self, request, mtd, good_id):
        """
        выполняет работу в зависимости от метода
        """
        view_key = GetKey.views_key(request)
        cache.delete(view_key)
        if mtd == 'add':
            GoodViewService.add_good_view(request, good_id)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        elif mtd == 'delete':
            GoodViewService.del_good_view(request, good_id)
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        elif mtd == 'check':
            GoodViewService.check_good_view(request, good_id)
        elif mtd == 'count':
            GoodViewService.get_good_view_count(request)


class SaleListView(ListView):
    context_object_name = 'discounts'
    template_name = 'app_market/sale_list.html'
    queryset = Discount.objects.filter(active=True)
    paginate_by = 8


class SaleView(DetailView):
    context_object_name = 'discount'
    model = Discount
    template_name = 'app_market/sale.html'
    paginate_by = 8

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        goods = Catalog.objects.filter(
            discount__id=pk).select_related(
            'good',
            'good__image',
            'good__category').order_by(
            'good__category__title',
            'good__good_type')[:20]

        goods = goods.annotate(avg_price=Avg('price'))
        context['goods'] = query_sale_annotate(goods)
        return context


class PopularGoodView(ListView):
    """
    Представление показывает список популярных товаров
    """
    queryset = Good.objects.filter(soft_delete=False).prefetch_related('catalog').select_related(
        'image', 'discount', 'category').annotate(avg_price=Avg('catalog__price')).annotate(
        popularity_index=Sum('catalog__popularity_index')).order_by('-popularity_index')[:8]
    template_name = 'app_market/shop.html'
    context_object_name = 'goods'


class OrderingView(TemplateView):
    """Вьюха оформления заказа находящегося в корзине"""

    def get(self, request: HttpRequest, basket=None, *args, **kwargs):
        form = OrderingForm()
        login_form = LoginForm()
        context = dict(form=form, check_step='0', basket=basket, login_form=login_form)
        return render(request, 'app_market/order.html', context=context)

    def post(self, request: HttpRequest):
        form = OrderingForm(request.POST)
        login_form = LoginForm(request.POST)
        check_step = request.POST.get('step', '0')
        context = dict(check_step=check_step,
                       form=form,
                       login_form=login_form)

        if login_form.is_valid():
            login(request, login_form.cleaned_data.get('user'))
            return redirect(reverse('ordering'))
        elif check_step == '0' and login_form.errors:
            context['login_error'] = True
        if check_step == '1':
            if request.user.is_authenticated:
                context['check_step'] = '1'
            elif form.is_valid():
                email = form.cleaned_data.get('email')
                password = form.cleaned_data.get('password1')
                form = form.save(commit=False)
                form.username = email
                form.set_password(password)
                form.save()
                user = authenticate(username=email, password=password)
                login(self.request, user)
                context['check_step'] = '0'
            else:
                context['check_step'] = '0'
        elif check_step == '2':
            # получим стоимость корзины
            basket, cart_amount_dict = CartService.get_goods_from_cart(request=request)
            if not basket:
                # если корзина пуста отправляем пользователя на главную страницу
                return redirect(reverse('index'))
            # формируем контекст
            context['check_step'] = '2'
            context['basket'] = basket
            if cart_amount_dict.get('discounted_total_price'):
                context['total_price'] = cart_amount_dict.get('discounted_total_price')
            else:
                context['total_price'] = cart_amount_dict.get('total_price')
            delivery_price = PayOrderService.get_delivery_price(
                delivery=request.POST.get('delivery'),
                price=context.get('total_price'),
                sellers_count=CartService.get_unique_seller_count(basket))
            context['total_price'] += delivery_price
            context['delivery_price'] = delivery_price
            pay_method = request.POST.get('pay')
            data = dict(delivery=request.POST.get('delivery'),
                        city=request.POST.get('city'),
                        address=request.POST.get('address'),
                        description=request.POST.get('description'),
                        pay_method=pay_method,
                        delivery_price=delivery_price,
                        status='pending')
            order = Order.objects.filter(
                Q(user=request.user) & Q(status='pending')).last()
            if order:
                Order.objects.filter(pk=order.pk).update(**data)
            else:
                data['user'] = request.user
                data['status'] = 'pending'
                Order.objects.create(**data)
        return render(request, 'app_market/order.html', context)


class PaymentFormView(FormView):
    """
    Вьюха отображения ввода карты в зависимости от выбора способа оплаты
    товара после оформления заказа (если в течении 15 минут не ввести номер карты,
    будет перевод на главную страницу)
    """
    form_class = PayForm
    success_url = reverse_lazy('payment_status')
    template_name = 'app_market/universe_payment.html'

    def get_initial(self):
        order = Order.objects.filter(Q(user=self.request.user) & Q(status='pending')).last()
        if not order:
            return redirect(reverse('index'))
        self.initial['pay_method'] = order.pay_method
        self.initial['order_id'] = order.pk
        self.kwargs['order'] = order
        return self.initial.copy()

    def get_context_data(self, **kwargs):
        """проверим, если заказ не существует, выкинем юзера на начало"""
        if 'form' not in kwargs:
            kwargs['form'] = self.get_form()
        delta_15_min = datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
        Order.objects.filter(user=self.request.user, created_at__gte=delta_15_min).last()
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        # редиректим юзера если у него пустая корзина
        goods, cart_amount_dict = CartService.get_goods_from_cart(request=self.request)
        if not goods or goods.count == 0:
            return HttpResponseRedirect(reverse_lazy('cart'))
        # сохраним данные для оплаты в платеже
        order_id = form.cleaned_data.get('order_id')
        card = form.cleaned_data.get('card_number')
        card = ''.join([letter for letter in card if letter.isdigit()])
        pay_method = form.cleaned_data.get('pay_method')
        amount = cart_amount_dict.get('discounted_total_price')
        sellers_count = CartService.get_unique_seller_count(goods)
        delivery_amount = PayOrderService.get_delivery_price(
            delivery=self.kwargs.get('order').delivery, price=float(amount), sellers_count=sellers_count)
        data = dict(order_id=order_id, amount=float(amount + delivery_amount), card=card, pay_method=pay_method)
        Order.objects.filter(pk=order_id).update(response=json.dumps(data, ensure_ascii=False))
        # запускаем сервис оплаты
        PayOrderService.pay_order(order_id)
        url = reverse_lazy('payment_status', kwargs={'order_id': order_id})
        return HttpResponseRedirect(url)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class ProgressPaymentView(View):
    """ Вьюха прогресса оплаты (на фронте стоит обновление страницы каждые 5 секунд)"""

    def get(self, request: HttpRequest, order_id: int):
        order = PayOrderService.get_order_by_id(order_id)
        if order.status == 'pay_success':
            CartService.delete_cache(request)
            messages.add_message(request, messages.INFO, _('order payment success'))
            return redirect(reverse_lazy('history_detail_order',
                                         kwargs=dict(pk=order_id)))
        elif order.status == 'error':
            CartService.delete_cache(request)
            messages.add_message(request, messages.INFO, _('order payment error'))
            return redirect(reverse_lazy('history_detail_order',
                                         kwargs=dict(pk=order_id)))
        else:
            context = dict(order_id=order_id, order=order)
            return render(request, 'app_market/progressPayment.html', context=context)


class HistoryOrderView(ListBreadcrumbMixin, ListView):
    context_object_name = 'orders'
    template_name = 'app_users/historyorder.html'
    crumbs = [(_('Order history'), '')]

    def get_queryset(self, **kwargs):
        queryset = Order.objects.filter(user=self.request.user).order_by('-pk')
        return queryset


class HistoryDetailOrderView(DetailBreadcrumbMixin, FormMixin, DetailView):
    """представление реализует детали заказа"""
    context_object_name = 'order'
    model = Order
    template_name = 'app_users/oneorder.html'
    form_class = PayForm
    success_url = reverse_lazy('payment_status')

    @property
    def crumbs(self, **kwargs):
        return [
            (_('Orders history'), reverse_lazy('history_order')), (f"{_('order')} №{self.kwargs.get('pk')}", '')
        ]

    def get_context_data(self, **kwargs):
        context = super(HistoryDetailOrderView, self).get_context_data()
        order = self.object
        # запросим все товары к заказу с зависимостями и отдадим в контекст
        details = OrderDetail.objects.filter(order=order)
        details = details.select_related('cart', 'discount', 'cart__catalog', 'cart__good',
                                         'cart__good__image',
                                         'cart__catalog__seller', 'cart__catalog__good',
                                         'cart__catalog__good__image')
        context['details'] = details
        return context

    def get_initial(self):
        """метод инициализирует форму миксина данными из объекта"""
        order = self.get_object()
        self.initial['pay_method'] = order.pay_method
        self.initial['order_id'] = order.pk
        self.initial['card_number'] = order.get_response().get('card', '12345678')
        return self.initial.copy()

    def post(self, request, *args, **kwargs):
        """метод инициирует проверку формы и повторную оплату"""
        order = self.get_object()
        order.status = 'repay'
        form = self.get_form()
        if form.is_valid():
            data: Dict[Any] = order.get_response()
            card = form.cleaned_data.get('card_number')
            card = ''.join([letter for letter in card if letter.isdigit()])
            data['card'] = card
            data.pop('error')
            data['status'] = 'pending'
            order.set_response(data)
            order.save()
            PayOrderService.pay_order(form.cleaned_data.get('order_id'))
            url = reverse_lazy('payment_status', kwargs={'order_id': form.cleaned_data.get('order_id')})
            return redirect(url)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class ContactsView(ListBreadcrumbMixin, FormView):
    template_name = 'app_market/contacts.html'
    form_class = MessagesForm
    success_url = reverse_lazy('successfully')
    crumbs = [(_('Contacts'), '')]

    def get_context_data(self, **kwargs):
        context = super(ContactsView, self).get_context_data()
        return context

    def form_valid(self, form):
        form.save()
        return super(ContactsView, self).form_valid(form)


class SuccessfullyView(View):
    """
    Вьюха вывода страницы с уведомление (Например при отправке сообщения в контактах)
    """

    def get(self, request, message=None):
        check_url = {'contacts': _('The message has been sent successfully!')}
        referer = self.request.META.get('HTTP_REFERER')

        if referer:
            referer = referer.split('/')[3]
            if referer in check_url.keys():
                message = check_url[referer]
            return render(request, 'base_part/successfully.html', {'text': message})
        else:
            return redirect(reverse_lazy('index'))


class CatalogView(ListBreadcrumbMixin, TemplateView):
    template_name = 'app_market/category.html'
    crumbs = [(_('Catalog'), reverse_lazy('sellers_list'))]
