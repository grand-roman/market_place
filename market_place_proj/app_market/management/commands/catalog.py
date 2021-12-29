import random
from typing import List

from django.core.management import BaseCommand

from app_market.models import Catalog, Category, Good, Seller
from tqdm import tqdm


def update_category_best_field():
    ids = list(Category.objects.filter(level=1).values_list('id', flat=True))
    ids = [id for id in ids if id % 15 == 0]
    Category.objects.filter(id__in=ids).update(best=True)


def set_spetial_offer_field(goods_queryset: List[int]):
    """установим метку на товар"""
    goods_queryset = [item for item in goods_queryset if item % 20 == 0]
    Good.objects.filter(id__in=goods_queryset).update(short_list=True)


class Command(BaseCommand):
    help = 'Генерация каталогов'

    def handle(self, *args, **options):
        update_category_best_field()
        Catalog.objects.all().delete()
        sellers = list(Seller.objects.values_list('id', flat=True))
        goods_queryset = list(Good.objects.values_list('id', flat=True))
        set_spetial_offer_field(goods_queryset)
        goods = []
        bar1 = tqdm(total=len(sellers), position=0)
        for seller_id in sellers:
            bar1.update()
            bar2 = tqdm(total=len(goods_queryset), position=1)
            for good_id in goods_queryset:
                bar2.update()
                goods.append(Catalog(
                    good_id=good_id,
                    seller_id=seller_id,
                    count=random.randint(1, 20),
                    price=round(random.uniform(500, 10000), 2),
                    popularity_index=random.randint(0, 100)
                ))

        Catalog.objects.bulk_create(goods)
        self.stdout.write("Каталоги сгенерированы")
