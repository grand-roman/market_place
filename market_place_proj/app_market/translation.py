from app_market.models import Category, Good, Seller, Stock, Tag
from modeltranslation.translator import TranslationOptions, translator


class CategoryTranslationOptions(TranslationOptions):
    fields = ('title',)


class GoodTranslationOptions(TranslationOptions):
    fields = ('title', 'maker', 'model', 'good_type', 'description')


class SellerTranslationOptions(TranslationOptions):
    fields = ('title', 'about_info', 'delivery_info', 'money_info', 'support_info', 'quality_info', 'phone_info',
              'address_info', 'mail_info', 'fb_info', 'tw_info', 'gg_info', 'in_info',
              'pt_info', 'ml_info')


class TagTranslationOptions(TranslationOptions):
    fields = ('title',)


class StockTranslationOptions(TranslationOptions):
    fields = ('title', 'content',)


translator.register(Category, CategoryTranslationOptions)
translator.register(Seller, SellerTranslationOptions)
translator.register(Stock, StockTranslationOptions)
translator.register(Good, GoodTranslationOptions)
translator.register(Tag, TagTranslationOptions)
