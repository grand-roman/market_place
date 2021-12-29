import random

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from app_market.models import Cart, CartSale, Catalog, Discount, Good, RelatedGoodGroup


User = get_user_model()


class Command(BaseCommand):
    help = 'Генерация корзины'

    def handle(self, *args, **options):
        groups = list(RelatedGoodGroup.objects.all())
        Cart.objects.all().delete()
        CartSale.objects.all().update(discount=None)
        CartSale.objects.all().delete()
        cart = []
        catalog = Catalog.objects.all()
        user = User.objects.get_or_create(
            username='test_user',
            phone='0000000000',
            is_email_verified=True,
            email='test_skillbox@mail.ru',
        )
        user[0].set_password('123')
        user[0].save()
        for group in random.sample(groups, 2):
            good1 = list(Good.objects.filter(group=group.group1))[0]
            good2 = list(Good.objects.filter(group=group.group2))[0]
            catalog1 = random.choice(list(catalog.filter(good=good1.pk)))
            catalog2 = random.choice(list(catalog.filter(good=good2.pk)))
            cart.append(Cart(good=good1, catalog=catalog1, count=1, user_id=user[0].pk))
            cart.append(Cart(good=good2, catalog=catalog2, count=1, user_id=user[0].pk))
        Cart.objects.bulk_create(cart)

        cart = []
        discounted_catalog = list(Good.objects.filter(catalog__discount__isnull=False))
        for good in random.sample(discounted_catalog, 3):
            good_catalog = random.choice(list(catalog.filter(good=good.pk)))
            cart.append(Cart(good=good, catalog=good_catalog, count=1, user_id=user[0].pk))
        Cart.objects.bulk_create(cart)

        cart = []
        discounts = Discount.objects.all()
        CartSale.objects.create(quantity=2, total_price=5000, discount=random.choice(discounts))
        CartSale.objects.create(quantity=1, total_price=10000, discount=random.choice(discounts))
        for cart_sale in CartSale.objects.all():
            goods = list(Catalog.objects.filter(price__gte=cart_sale.total_price / 2))[:cart_sale.quantity]
            for good in goods:
                cart.append(Cart(good=good.good, catalog=good, count=1, user_id=user[0].pk))
        Cart.objects.bulk_create(cart)
        self.stdout.write("Корзина сгенерирована")
