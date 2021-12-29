from django import template

from app_market.models import Good, Review


register = template.Library()


@register.inclusion_tag('app_market/widgets/product/tabs/review_tab.html')
def get_comments(pk):
    """
    Вывод товаров на странице каталогов
    :return: context
    """
    # TODO Написать и продумать аннотацию при присутствии скидки на товар

    review = Review.objects.filter(good_id=pk, soft_delete=False).select_related('user', 'good').all()

    context = {'review': review}
    return context


@register.inclusion_tag('app_market/product.html')
def get_detail_product(pk):
    good = Good.objects.filter(pk=pk).first()
    context = {'good': good}
    return context
