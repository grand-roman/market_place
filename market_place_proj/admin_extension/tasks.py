
import json
import logging
import pathlib
import shutil

from django.core.mail import send_mail

import environ
import requests
from admin_extension.models import Files
from app_market.models import Catalog, Category, Good, MediaFiles, Seller
from transliterate import translit

from market_place_proj.celery import app


logger = logging.getLogger('about_import')

ROOT = environ.Path(__file__) - 2

IMPORT_NICE_DIRECTORY = ROOT + 'media/imports/nice/'
IMPORT_PROBLEM_DIRECTORY = ROOT + 'media/imports/problem/'


def moving_files(file, name_file, file_name, json_file, status):
    if status == 'nice':
        path = f'imports/nice/{name_file}'
        directory = IMPORT_NICE_DIRECTORY
    else:
        path = f'imports/problem/{name_file}'
        directory = IMPORT_PROBLEM_DIRECTORY

    Files.objects.filter(file_start=file.file_start).update(
        file_start=None, file_nice=path)
    pathlib.Path(directory).mkdir(parents=True, exist_ok=True)
    shutil.move(ROOT + file_name, directory + (json_file[0]['seller']['title_ru'] + name_file))


def open_images(urls):
    for url in urls:
        try:
            file_open = url.split('/')[-1]
            directory = ROOT + 'media/catalog/images/'
            pathlib.Path(directory).mkdir(parents=True, exist_ok=True)
            path = directory + file_open
            image = f'catalog/images/{file_open}'
            with open(path, 'wb') as file:
                try:
                    file.write(requests.get(url).content)
                except BaseException as exc:
                    logger.warning(msg=f'картинку {url} не удалось скачать, ошибка {exc}')
            return image
        except BaseException as exc:
            logger.warning(msg=f'картинка {url} не импортирована, ошибка {exc}')
            return None


def create_good(goods, category, list_json_file):
    for good in goods:
        new_good = Catalog.objects.create(
            good=Good.objects.create(
                title=good['title'],
                title_ru=good['title'],
                title_en=translit(good['title'], language_code='ru', reversed=True),
                description=json.dumps(good['description'], ensure_ascii=False),
                description_ru=json.dumps(good['description'], ensure_ascii=False),
                description_en=json.dumps(translit(good['description'], language_code='ru', reversed=True), ensure_ascii=False),
                category=Category.objects.get_or_create(title=category['title'])[0],
                image=MediaFiles.objects.get_or_create(
                    file=open_images(urls=[good['image']]))[0]
            ),
            seller=Seller.objects.get_or_create(
                title=list_json_file[0]['seller']['title_ru'],
                title_ru=list_json_file[0]['seller']['title_ru'],
                title_en=list_json_file[0]['seller']['title_en'],
            )[0],
            price=good['price'],
            count=good['count'],
        )
        for image in good['files']:
            if image is not None:
                url = MediaFiles.objects.get_or_create(file=open_images(urls=[image]))[0]
                new_good.good.files.add(url)
        logger.log(msg=f'товар {good["title"]} импортирован')
    logger.log(msg=f'категория {category["title"]} импортирована')
    return True


@app.task
def import_file(email):
    for file in Files.objects.filter(file_start__isnull=False):
        file_name = f'media/{file.file_start}'
        name_file = file_name.split('/')[-1]
        if file_name.endswith('.json') is True:
            try:
                with open(file_name, 'r') as json_file:
                    list_json_file = json.load(json_file)
                    for _, categories in list_json_file[1].items():
                        for category in categories:
                            if Category.objects.filter(title=category['title']).exists():
                                goods = category['goods']
                                create_good(goods, category, list_json_file)
                            else:
                                logger.error(msg=f'не стандартная категория {category["title"]} импорт не удался')

                moving_files(file=file,
                             name_file=name_file,
                             file_name=file_name,
                             json_file=list_json_file, status='nice')
                logger.log(f'файл {name_file} импортирован')
            except BaseException as exc:
                logger.error(msg=f'при импорте файла {name_file} произошла ошибка {exc}')
                moving_files(file=file, name_file=name_file, file_name=file_name, json_file=list_json_file,
                             status='problem')
        else:
            logger.error(msg=f'файл {name_file} должен быть в формате json, импорт не произведён')
            moving_files(file=file,
                         name_file=name_file,
                         file_name=file_name,
                         json_file=list_json_file, status='problem')

    if email:
        send_mail(
            'Импорт произведён',
            'email@gmail.com',
            [email],
            fail_silently=False,
        )
