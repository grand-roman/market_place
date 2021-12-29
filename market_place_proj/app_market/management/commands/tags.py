import json
import os
import sys

from django.core.management import BaseCommand

from app_market.models import Category, Good, Tag
from tqdm import tqdm


def tag_gen(*args):
    """
    вернем идентификатор тега
    """
    tags = args[0]
    index = -1
    while True:
        if index + 1 == len(tags):
            index = 0
        else:
            index += 1
        yield tags[index]


class Command(BaseCommand):
    help = 'Генерация продавцов и их пользователей'

    def handle(self, *args, **options):
        Tag.objects.all().delete()
        path = os.path.join(os.path.split(sys.argv[0])[0], 'app_market', 'management', 'commands', 'tags.json')
        with open(path, 'r', encoding='UTF-8') as fl:
            tags = json.load(fl)
        tags_titles = tag_gen(tags)
        cats = Category.objects.filter(children=None)
        good_groups = []
        bar = tqdm(total=len(cats))
        for cat_index, cat in enumerate(cats):
            bar.update()
            goods = cat.good.values_list('id', flat=True)
            for index in range(10):
                item = next(tags_titles)
                tag = Tag.objects.create(title=item['ru'], title_ru=item['ru'], title_en=item['en'])
                good_groups.extend(
                    [Good.tag.through(good_id=good, tag_id=tag.id) for good in goods if good % (index + 1) == 0])
        Good.tag.through.objects.bulk_create(good_groups)
        print('finished')
