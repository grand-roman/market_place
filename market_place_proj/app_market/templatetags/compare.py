from django import template

from app_market.utils import CompareService


register = template.Library()


@register.inclusion_tag('app_market/widgets/compare.html')
def get_compare_icon(request):
    """
    Тэг возвращает иконку сравнения товаров, у цифрой
    """
    context = dict(compare_count=CompareService.count(request))
    return context
