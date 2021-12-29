import json
import uuid

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from autoslug import AutoSlugField
from model_utils import FieldTracker
from mptt.models import MPTTModel, TreeForeignKey

from market_place_proj.settings import good_cache_key_list


class GetKey:
    """класс генерирует ключи для кэша в зависимости от ситуации"""
    @classmethod
    def best_cats_key(cls):
        return 'best_cats'

    @classmethod
    def hot_offers_key(cls):
        """метод возвращает ключ для товаров со скидками"""
        return 'hot_offerts'

    @classmethod
    def limit_edition_key(cls, ):
        """
        Метод достаёт ключ для ограниченной серии товаров
        """
        return 'limit_edition'

    @classmethod
    def views_key(cls, request):
        """
        Метод достаёт ключ для сравнения чтобы найти список просмотренных товаров
        """
        return cls._get_key(request, 'good_views')

    @classmethod
    def compare_key(cls, request):
        """
        Метод достаёт ключ для сравнения чтобы найти список товаров в кэше
        """
        return cls._get_key(request, 'compare')

    @classmethod
    def cart_key(cls, request):
        """
        Метод достаёт ключ для поиска корзины в кэше
        """
        return cls._get_key(request, 'cart')

    @classmethod
    def cart_count_key(cls, request):
        """
        Метод достаёт ключ для поиска количества товаров в корзине в кэше
        """
        return cls._get_key(request, 'cart_count')

    @classmethod
    def anonymous_key(cls, request):
        """
        Метод достаёт ключ для сравнения чтобы найти список товаров в кэше
        """
        return cls._get_key(request, '')

    @classmethod
    def _get_key(cls, request, mask: str):
        """
        Метод генерирует ключ для поиска чего-то пользовательского в кэше.
        используется или user.id или случайно сгенерированный uuid
        маска разграничивает виды кэша
        """
        user_id_for_cache = request.session.get('user_id')
        if not user_id_for_cache:
            user_id_for_cache = uuid.uuid4().hex
            request.session['user_id'] = user_id_for_cache
        if not mask:
            return user_id_for_cache
        result = f'{mask}:{user_id_for_cache}'
        return result


class Seller(models.Model):
    """
    модель расширяет профиль пользователя доп. информацией о нем как о продавце
    """
    title = models.CharField(_('seller name'), max_length=100, db_index=True, unique=True)
    about_info = models.TextField(_('story'), null=True, blank=True)
    delivery_info = models.CharField(_('delivery'), max_length=255, null=True, blank=True)
    money_info = models.CharField(_('money'), max_length=255, null=True, blank=True)
    support_info = models.CharField(_('support'), max_length=255, null=True, blank=True)
    quality_info = models.CharField(_('quality'), max_length=255, null=True, blank=True)
    phone_info = models.CharField(_('phone'), max_length=255, null=True, blank=True)
    address_info = models.CharField(_('address'), max_length=255, null=True, blank=True)
    mail_info = models.CharField(_('mail'), max_length=255, null=True, blank=True)
    fb_info = models.CharField(_('FaceBook'), max_length=255, null=True, blank=True)
    tw_info = models.CharField(_('Twitter'), max_length=255, null=True, blank=True)
    gg_info = models.CharField(_('Google+'), max_length=255, null=True, blank=True)
    in_info = models.CharField(_('In'), max_length=255, null=True, blank=True)
    pt_info = models.CharField(_('Pt'), max_length=255, null=True, blank=True)
    ml_info = models.CharField(_('mail'), max_length=255, null=True, blank=True)
    icon = models.ImageField(_('icon'), upload_to='catalog/%Y/%m/%d/', null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('seller')
        verbose_name_plural = _('sellers')


class GoodGroup(models.Model):
    """
    модель определяет принадлежность товара к какому-либо набору для расчета скидки
    """
    title = models.CharField(max_length=100, verbose_name=_('product group for discount'))
    code = models.IntegerField(unique=True, db_index=True, verbose_name=_('product group code for the discount'))

    def __str__(self):
        return f'{self.title} :: {self.code}'

    class Meta:
        verbose_name = _('group of products for discount')
        verbose_name_plural = _('groups of products for discounts')


class DiscountVariants(models.Model):
    """
    модель позволяет определить, что за скидка:
    процент к цене
    фиксированная цена
    скидка в процентах от цены
    """
    title = models.CharField(max_length=100, verbose_name=_('discount option'))

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('discount option')
        verbose_name_plural = _('Discount options')


class Discount(models.Model):
    """
    модель реализует систему скидок
    """
    title = models.CharField(max_length=100, verbose_name=_('name of the discount'))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('time of discount creation'))
    closed_at = models.DateTimeField(db_index=True, verbose_name=_('discount completion time'))
    size = models.PositiveIntegerField(verbose_name=_('discount amount'))
    weight = models.PositiveIntegerField(verbose_name=_('discount weight'))
    variants = models.ForeignKey(DiscountVariants, on_delete=models.PROTECT, related_name='discount',
                                 verbose_name=_('discount options'))
    active = models.BooleanField(default=False, verbose_name=_('discount activated'))
    soft_delete = models.BooleanField(default=False, verbose_name=_('discount removed'))

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('Discount')
        verbose_name_plural = _('Discounts')


class Tag(models.Model):
    """
    тэг товара
    """
    title = models.CharField(_('tag'), db_index=True, max_length=50)

    def __str__(self):
        return self.title


class Category(MPTTModel):
    """
    общий каталог товаров (не путать с частным набором товаров у каждого продавца)
    """
    # локализация только категорий товаров.
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    title = models.CharField(max_length=300, db_index=True, verbose_name=_('product category name'))
    code = models.IntegerField(unique=True, db_index=True, verbose_name=_('product category code'))
    # и что делать со связями товаров после мягкого удаления?
    soft_delete = models.BooleanField(default=False, verbose_name=_('category removed'))
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT, blank=True, null=True, default=None,
                                 related_name='category', verbose_name=_('discount'))
    slug = AutoSlugField(_('slug'), populate_from='title_en', unique=True)
    icon = models.ForeignKey('MediaFiles', related_name='icon', blank=True, null=True,
                             verbose_name=_('related files'), on_delete=models.CASCADE)
    best = models.BooleanField(_('best'), default=False)

    def __str__(self):
        return self.title

    class MPTTMeta:
        order_insertion_by = ['title']
        verbose_name = _('Product category')
        verbose_name_plural = _('Product categories')


class MediaFiles(models.Model):
    """
    хранилище файлов для базы.
    """
    hash = models.CharField(max_length=100, null=True, blank=True)
    title = models.CharField(max_length=255, verbose_name=_('file description'))
    # filename = возможно не нужен
    filename = models.CharField(max_length=255, verbose_name=_('file name'))
    file = models.FileField(upload_to='catalog/%Y/%m/%d/', verbose_name=_('File'), null=True)
    link = models.TextField(_('link'), null=True)

    def __str__(self):
        return f'file: {self.file}'

    class Meta:
        verbose_name = _('File')
        verbose_name_plural = _('Files')


class Good(models.Model):
    title = models.CharField(_('good name'), max_length=500, db_index=True)
    maker = models.CharField(_('good maker'), max_length=500, db_index=True, blank=True, null=True)
    model = models.CharField(_('good model'), max_length=300, db_index=True, blank=True, null=True)
    good_type = models.CharField(_('type of goods'), max_length=500, db_index=True, blank=True, null=True)
    description = models.TextField(_('product description'))
    group = models.ForeignKey(GoodGroup, on_delete=models.PROTECT, blank=True, null=True, related_name='group',
                              verbose_name=_('group of products for discount'))
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='good',
                                 verbose_name=_('Product category'))
    short_list = models.BooleanField(_('special offer'), default=False, db_index=True)
    image = models.ForeignKey(MediaFiles,
                              on_delete=models.PROTECT,
                              related_name='good',
                              verbose_name=_('image for good'),
                              null=True)
    files = models.ManyToManyField(MediaFiles, related_name='catalog', blank=True, verbose_name=_('related files'))
    soft_delete = models.BooleanField(_('the product has been removed'), default=False)
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT, related_name='good',
                                 blank=True, null=True, default=None,
                                 verbose_name=_('discount'))
    view_count = models.PositiveIntegerField(_('the number of product views'), default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('product creation date'))
    tag = models.ManyToManyField(Tag, related_name='good', verbose_name=_('Tags'))

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')


class GoodView(models.Model):
    """
    модель реализует просмотры товаров
    """
    good = models.ForeignKey(
        Good, on_delete=models.PROTECT, related_name='views', verbose_name=_('good')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='views', verbose_name=_('user')
    )
    updated_at = models.DateTimeField(auto_now=True, db_index=True, verbose_name=_('updated at'))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('created at'))


class Review(models.Model):
    """
    модель хранит данные о всех отзывах, которые написал пользователь сайта
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews', verbose_name=_('user')
    )
    good = models.ForeignKey(
        Good, on_delete=models.PROTECT, related_name='review', verbose_name=_('product connection')
    )
    text = models.TextField(verbose_name=_('Review text'))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('time of writing the review'))
    soft_delete = models.BooleanField(default=False, verbose_name=_('review deleted'))

    def __str__(self):
        return f'feedback to: {self.good}'

    class Meta:
        verbose_name = _('Product Review')
        verbose_name_plural = _('Product Reviews')


class Delivery(models.Model):
    """
    модель реализует варианты доставки. Платная, бесплатная.
    """
    title = models.CharField(max_length=100, verbose_name=_('delivery name'))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('shipping cost'))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('delivery clearance time'))
    closed_at = models.DateTimeField(db_index=True, verbose_name=_('delivery completion time'))

    def __str__(self):
        return f'Order delivery {self.created_at} N {self.id}'

    class Meta:
        verbose_name = _('Delivery')
        verbose_name_plural = _('Delivery')


class Payment(models.Model):
    """
    модель реализует варианты доставки. Платная, бесплатная.
    """
    order = models.ForeignKey('Order', on_delete=models.PROTECT,
                              related_name='pay', verbose_name=_('order'))
    status = models.CharField(max_length=20, verbose_name=_('payment status'))
    card = models.CharField(max_length=8, verbose_name=_('payment card'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('payment time'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('updated'))

    def __str__(self):
        return f'Payment from {self.created_at} for the amount of: {self.status} moneys'

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')


class Catalog(models.Model):
    """
    модель реализует хранение каталога товаров для конкретного продавца
    """
    good = models.ForeignKey(Good, on_delete=models.PROTECT, related_name='catalog', verbose_name=_('product'))
    seller = models.ForeignKey(Seller, on_delete=models.PROTECT, related_name='catalog', verbose_name=_('seller'))
    price = models.DecimalField(_('price'), max_digits=10, decimal_places=2)
    count = models.PositiveIntegerField(_('quantity'), default=0)
    view_count = models.PositiveIntegerField(_('number of views'), default=0)
    soft_delete = models.BooleanField(_('soft delete'), default=False)
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT, blank=True, null=True, default=None,
                                 related_name='catalog', verbose_name=_('discount'))
    popularity_index = models.PositiveIntegerField(_('popularity'), default=0)
    delivery = models.ForeignKey(Delivery, verbose_name=_('delivery'), on_delete=models.PROTECT, blank=True,
                                 null=True, related_name='catalog')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True,
                                      verbose_name=_('date of creation of the catalog'))

    def __str__(self):
        return f'{self.seller.title} // {self.price} // {self.count} // {self.good.title}'[:50]

    class Meta:
        verbose_name = _('The sellers product catalog')
        verbose_name_plural = _('The sellers product catalog')


class Cart(models.Model):
    """
    Модель корзины покупателя
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cart',
        verbose_name=_('user'),
        null=True, blank=True
    )
    anon_user = models.CharField(_('anonymous ID'),
                                 null=True, blank=True,
                                 max_length=64,
                                 db_index=True)
    catalog = models.ForeignKey(Catalog,
                                on_delete=models.PROTECT,
                                null=True, blank=True,
                                related_name='cart',
                                verbose_name='catalog_good')
    good = models.ForeignKey(Good,
                             on_delete=models.PROTECT,
                             null=True, blank=True,
                             related_name='cart',
                             verbose_name=_('good'))
    count = models.PositiveIntegerField(_('quantity of goods'),
                                        null=True, blank=True)
    cart_discount = models.ForeignKey(Discount, on_delete=models.PROTECT, blank=True, null=True,
                                      default=None, related_name='cart', verbose_name=_('discount'))
    soft_delete = models.BooleanField(_('deleted'), default=False, db_index=True)

    class Meta:
        verbose_name = _('good in cart')
        verbose_name_plural = _('goods in cart')

    def __str__(self):
        return self.catalog.good.title


class Order(models.Model):
    """
    модель реализует хранение заказов с реквизитами
    """
    DELIVERY = [
        (_('ordinary'), _('Ordinary')),
        (_('express delivery'), _('Express delivery')),
    ]
    PAYMENT_METHOD = [
        (_('online'), _('online')),
        (_('someone'), _('someone')),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='order', verbose_name=_('user')
    )
    delivery = models.CharField(max_length=20, choices=DELIVERY, verbose_name=_('delivery'))
    city = models.CharField(max_length=50, db_index=True, verbose_name=_('city'))
    address = models.TextField(null=True, blank=True, verbose_name=_('delivery address'))
    description = models.TextField(null=True, blank=True, verbose_name=_('order description'))
    pay_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, verbose_name=_('pay method'))
    closed = models.BooleanField(default=False, verbose_name=_('order finish'))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('order creation time'))
    closed_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name=_('order completion time'))
    # подумать, возможно её стоит перенести в товары!!!
    delivery_price = models.DecimalField(max_digits=10, null=True, blank=True, decimal_places=2,
                                         verbose_name=_('shipping cost'))
    soft_delete = models.BooleanField(null=True, blank=True, default=False, verbose_name=_('order deleted'))
    status = models.CharField(max_length=20, verbose_name=_('payment status'), db_index=True)
    response = models.TextField(verbose_name=_('payment response'))
    cart_discount = models.ForeignKey(Discount, on_delete=models.PROTECT, default=None,
                                      blank=True, null=True, related_name='order',
                                      verbose_name=_('discount'))

    def __str__(self):
        return f'order from {self.created_at} N {self.id}'

    def get_response(self):
        """
        метод десериализирует ответ апи
        """
        return json.loads(self.response)

    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')

    def get_response(self):
        """
        метод десериализирует ответ апи
        """
        return json.loads(self.response)

    def set_response(self, data):
        self.response = json.dumps(data, ensure_ascii=False)
        self.save()


class OrderDetail(models.Model):
    """
    модель реализует хранение товаров в корзине и в заказе
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='order_detail',
        verbose_name=_('order'),
        null=True, blank=True
    )
    order = models.ForeignKey(Order,
                              on_delete=models.PROTECT,
                              related_name='detail',
                              null=True, blank=True,
                              verbose_name=_('order'))
    cart = models.ForeignKey(Cart,
                             on_delete=models.PROTECT,
                             related_name='order_detail',
                             null=True, blank=True,
                             verbose_name=_('Cart'))
    price = models.DecimalField(_('product price'), max_digits=10, decimal_places=2, null=True, blank=True)
    count = models.PositiveIntegerField(_('quantity of goods'), null=True, blank=True)
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT, default=None,
                                 blank=True, null=True, related_name='detail',
                                 verbose_name=_('discount'))
    # мягкое удаление только для оформленных заказов
    soft_delete = models.BooleanField(_('the product has been removed'), default=False)

    def __str__(self):
        return f'product price: {self.price} count: {self.count}'

    class Meta:
        verbose_name = _('Order Details')
        verbose_name_plural = _('Order Details')


class Stock(models.Model):
    """
    Модель акций для слайдера.

    Attributes
        title: Название
        content: Контент
        link: Ссылка
        image: Изображение
        is_active: Активность
        sort: Сортировка
    """
    title = models.CharField(_('Title'), max_length=100)
    content = models.TextField(_('Content'), max_length=255, blank=True, null=True)
    link = models.URLField(_('Link'), max_length=1000, blank=True, null=True)
    image = models.ImageField(_('Image'), upload_to='stock', blank=True, null=True)
    image_link = models.CharField(_('Image_link'), max_length=255, blank=True, null=True, default=None)
    is_active = models.BooleanField(_('Activity'), default=True)
    sort = models.IntegerField(_('Sort'), default=100)

    tracker = FieldTracker()

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('Stock')
        verbose_name_plural = _('Stocks')


@receiver(post_save, sender=Stock)
def post_save_stock(sender, instance, created: bool, **kwargs):
    model_fields = [f.name for f in sender._meta.get_fields()]
    changed_fields = any([instance.tracker.has_changed(field) for field in model_fields])
    if changed_fields or created:
        cache.delete('slider_stocks')


@receiver(post_delete, sender=Stock)
def post_delete_stock(sender, instance, **kwargs):
    cache.delete('slider_stocks')


@receiver([post_save, post_delete], sender=Category)
def post_edit_category(sender, instance, **kwargs):
    cache.delete('category')


@receiver([post_save, post_delete], sender=Review)
def post_edid_review(sender, instance, **kwargs):
    for i in good_cache_key_list:
        cache.delete(i)
    cache.delete(f'detail_prod_obj-{instance.good.pk}')


@receiver([post_save, post_delete], sender=Good)
def post_edit_good(sender, instance, **kwargs):
    for i in good_cache_key_list:
        cache.delete(i)
    cache.delete(f'detail_prod_obj-{instance.pk}')


@receiver(user_logged_in)
def update_user_in_cart(sender, user, request, **kwargs):
    """
    обработаем товары в корзине при авторизации юзера
    """
    cache.delete(GetKey.cart_key(request))
    cache.delete(GetKey.cart_count_key(request))
    Cart.objects.filter(
        anon_user=GetKey.anonymous_key(request)
    ).update(
        user=user,
        anon_user=user.pk
    )
    request.session['user_id'] = user.pk


class RelatedGoodGroup(models.Model):
    """
    модель реализует скидки на наборы
    """
    group1 = models.ForeignKey(GoodGroup, on_delete=models.PROTECT, blank=True, null=True, related_name='group1',
                               verbose_name=_('Product category 1'))
    group2 = models.ForeignKey(GoodGroup, on_delete=models.PROTECT, blank=True, null=True, related_name='group2',
                               verbose_name=_('Product category 2'))
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT, blank=True, null=True, default=None,
                                 related_name='related_discounts', verbose_name=_('discount'))


class CartSale(models.Model):
    """
    модель реализует скидку на корзину
    """
    quantity = models.PositiveIntegerField(verbose_name=_('quantity'))
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('total_price'))
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT, blank=True, null=True, default=None,
                                 related_name='cart_sale', verbose_name=_('discount'))


class MessagesModel(models.Model):
    name = models.CharField(_('Name'), max_length=128)
    mail = models.EmailField(_('Email'))
    website = models.URLField(_('Website'))
    message = models.TextField(_('Message'), max_length=512)
    created_at = models.DateTimeField(_('Message creation time'), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
