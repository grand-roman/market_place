from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from app_market.models import (
    Cart,
    CartSale,
    Catalog,
    Category,
    Delivery,
    Discount,
    DiscountVariants,
    Good,
    GoodGroup,
    MediaFiles,
    MessagesModel,
    Order,
    Payment,
    RelatedGoodGroup,
    Review,
    Seller,
    Stock,
)
from mptt.admin import MPTTModelAdmin


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ['title', 'about_info']
    search_fields = ['title']


@admin.register(GoodGroup)
class GoodGroupAdmin(admin.ModelAdmin):
    list_display = ['title', 'code']
    search_fields = ['title']


@admin.register(DiscountVariants)
class DiscountVariantsAdmin(admin.ModelAdmin):
    list_display = ['title']
    search_fields = ['title']


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_select_related = ('variants',)
    list_display = ['id', 'title', 'active', 'soft_delete', 'variants', 'weight']
    list_display_links = ['title']
    search_fields = ['title']

    actions = ['activation', 'deactivation']

    def activation(self, request, queryset):
        queryset.update(active=True)

    def deactivation(self, request, queryset):
        queryset.update(active=False)

    activation.short_description = 'Применить скидку'
    deactivation.short_description = 'Отменить скидку'


@admin.register(RelatedGoodGroup)
class RelatedGoodGroupAdmin(admin.ModelAdmin):
    search_fields = ('group1', 'group2',)


@admin.register(CartSale)
class CartSaleAdmin(admin.ModelAdmin):
    pass


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    fields = ('count', 'good', 'catalog', 'user')
    list_display = ['user', 'title', 'seller', 'price', 'count', 'full_price']
    list_display_links = ['user', 'title']
    list_select_related = ('user', 'good', 'catalog', 'catalog__seller', 'catalog__good')
    search_fields = (
        'user__username__exact', 'catalog__good__title_ru', 'catalog__good__title_en', 'catalog__seller__title_ru',
        'catalog__seller__title_en')
    raw_id_fields = ['good', 'catalog', 'user']

    def title(self, obj):
        return obj.catalog.good.title

    def price(self, obj):
        return obj.catalog.price

    def full_price(self, obj):
        return obj.catalog.price * obj.count

    def seller(self, obj):
        return obj.catalog.seller.title


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    mptt_level_indent = 20

    autocomplete_fields = ['parent', 'icon', 'discount']
    list_display = ['title', 'code', 'parent', 'discount', 'soft_delete']
    list_filter = ['soft_delete']
    search_fields = ['title', 'title_ru', 'title_en']
    raw_id_fields = ['icon']


@admin.register(Good)
class GoodAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'discount', 'soft_delete']
    list_filter = ['soft_delete', 'discount', 'short_list']
    search_fields = ['title', 'category__title']
    raw_id_fields = ['group', 'image', 'files']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['good', 'user', 'created_at', 'soft_delete']
    list_filter = ['soft_delete']
    search_fields = ['good__title', 'user', 'text']


@admin.register(MediaFiles)
class MediaFilesAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'filename']
    list_display_links = ['title']
    search_fields = ['file', 'title']


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'created_at', 'closed_at']
    search_fields = ['title', 'code']


class FilterPrice(admin.SimpleListFilter):
    title = _('Price')
    parameter_name = 'price'

    def lookups(self, request, model_admin):
        return (
            ('1', _('to 1000')),
            ('2', _('from 1000 to 10000')),
            ('3', _('from 10000 to 50000')),
            ('4', _('from 50000')),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(price__lte=1000)
        if self.value() == '2':
            return queryset.filter(price__range=[1000, 10000])
        if self.value() == '3':
            return queryset.filter(price__range=[10000, 50000])
        if self.value() == '4':
            return queryset.filter(price__gte=50000)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'created_at']
    list_filter = ['order', 'status', FilterPrice]
    search_fields = ['created_at', 'status']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'closed', 'soft_delete']
    list_filter = ['closed', 'soft_delete']
    search_fields = ['user_username', 'code', 'city', 'address']


@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    autocomplete_fields = ['good', 'seller', 'discount']
    list_display = ['seller', 'good', 'price', 'count', 'discount', 'soft_delete']
    list_display_links = ['good']
    list_filter = ['soft_delete']
    list_select_related = ['good', 'seller']
    search_fields = ['good__title_ru', 'good__title_en', 'seller__title_ru', 'seller__title_en', 'good__group__title']


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'is_active', 'sort']
    list_display_links = ('title',)


@admin.register(MessagesModel)
class MessagesAdmin(admin.ModelAdmin):
    list_display = ['name', 'mail', 'message']
    list_filter = ['name']
    search_fields = ['name', 'mail']
