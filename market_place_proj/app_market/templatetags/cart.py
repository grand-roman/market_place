from django import template

from app_market.utils import CartService


register = template.Library()


@register.inclusion_tag('app_market/widgets/cart.html')
def get_cart_icon(request):
    """
    Тэг возвращает иконку корзины, с цифрой
    """
    context = dict(cart=CartService.get_header_info(request))
    return context
