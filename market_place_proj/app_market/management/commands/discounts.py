import random
from datetime import datetime, timedelta

from django.core.management import BaseCommand
from django.utils import timezone

from app_market.models import (
    CartSale,
    Catalog,
    Category,
    Discount,
    DiscountVariants,
    Good,
    GoodGroup,
    RelatedGoodGroup,
)
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Генерация скидок'

    def handle(self, *args, **options):
        Catalog.objects.all().update(discount=None)
        Good.objects.all().update(discount=None, group=None)
        Category.objects.all().update(discount=None)
        RelatedGoodGroup.objects.all().update(discount=None, group1=None, group2=None)
        CartSale.objects.all().update(discount=None)
        GoodGroup.objects.all().delete()
        Discount.objects.all().delete()
        RelatedGoodGroup.objects.all().delete()
        CartSale.objects.all().delete()
        discounts = []
        variants = {'Percent': random.choice([20, 50, 80]), 'Sum': random.choice([200, 500, 1000]),
                    'Fixed': random.choice([200, 500, 1000])}
        goods_by_category = {}

        bar = tqdm(total=len(Good.objects.order_by('category').all()))
        bar.set_description(desc='смотрим товары и категории')
        for good in Good.objects.order_by('category').all():
            bar.update()
            if good.category.title not in goods_by_category:
                goods_by_category[good.category.title] = []
            goods_by_category[good.category.title].append(good)
        bar.close()
        new_discounted_goods = []

        for category, goods in goods_by_category.items():
            for good in random.sample(goods, round(len(goods) / 4)):
                new_discounted_goods.append(good)

        bar = tqdm(total=len(new_discounted_goods))
        bar.set_description(desc='итерация по new_discounted_goods')
        disc_variants = DiscountVariants.objects.all()
        for index, good in enumerate(new_discounted_goods):
            bar.update()
            variant = random.choice(disc_variants)
            discounts.append(Discount(title=f'Discount {index}',
                                      created_at=datetime.utcnow(),
                                      closed_at=timezone.now() + timedelta(weeks=1),
                                      size=variants[variant.title],
                                      weight=random.randint(1, len(new_discounted_goods)),
                                      variants=variant,
                                      active=True))
        print('create...')
        Discount.objects.bulk_create(discounts)
        print('ассоциации товаров с ссылками завершены')
        bar.close()

        bar = tqdm(total=len(new_discounted_goods))
        bar.set_description(desc='итерация по new_discounted_goods')
        discounts = Discount.objects.all()

        discounted_sellers = []
        discounted_categories = []
        for good in new_discounted_goods:
            bar.update()
            category = Category.objects.get(pk=good.category.pk)
            category.discount = random.choice(discounts)
            good.discount = random.choice(discounts)
            discounted_categories.append(category)
            sellers = Catalog.objects.filter(good__pk=good.pk)
            for seller in sellers:
                seller.discount = random.choice(discounts)
                discounted_sellers.append(seller)

        Good.objects.bulk_update(new_discounted_goods, ['discount'])
        Category.objects.bulk_update(discounted_categories, ['discount'])
        Catalog.objects.bulk_update(discounted_sellers, ['discount'])

        related_groups_count = 4
        for i in range(1, related_groups_count):
            group1 = get_random_goods(new_discounted_goods, round(len(new_discounted_goods) / 4))
            group2 = get_random_goods(new_discounted_goods, round(len(new_discounted_goods) / 4))
            good_group1 = GoodGroup(title=f'Good Group_first_{i}', code=i * 50)
            good_group2 = GoodGroup(title=f'Good Group_second_{i}', code=i + 1 * 100)
            good_group1.save(), good_group2.save()
            Good.objects.filter(id__in=group1).update(group=good_group1)
            Good.objects.filter(id__in=group2).update(group=good_group2)
            RelatedGoodGroup.objects.create(group1=good_group1, group2=good_group2, discount=random.choice(discounts))
        bar.close()
        print('ассоциации товаров с группами завершены')
        self.stdout.write("Скидки сгенерированы")


def get_random_goods(goods, n):
    random.shuffle(goods)
    for good in goods[:n]:
        yield good.id
