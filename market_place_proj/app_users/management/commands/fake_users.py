import random

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.core.management import BaseCommand

import requests
from faker import Faker


User = get_user_model()
fake = Faker()

# Документация api для генерации пользователей https://avatars.dicebear.com/docs/http-api
ICONS_URL = 'https://avatars.dicebear.com/api/'
ICONS_TYPES = [
    'adventurer',
    'adventurer-neutral',
    'avataaars',
    'big-ears',
    'big-ears-neutral',
    'big-smile',
    'bottts',
    'croodles',
    'croodles-neutral',
    'gridy',
    'identicon',
    'initials',
    'jdenticon',
    'micah',
    'miniavs',
    'open-peeps',
    'personas',
    'pixel-art',
    'pixel-art-neutral',
]


def upload_avatar(full_name, gender, type='initial'):
    file_name = f'{full_name}.svg'.lower().replace(" ", "-")
    image_url = f'{ICONS_URL}{type}/{gender}/{file_name}'
    response = requests.get(image_url)
    img_temp = None

    if response.status_code == 200:
        # Сохранение изображения во временный файл
        img_temp = NamedTemporaryFile()
        img_temp.write(response.content)
        img_temp.flush()

    return file_name, img_temp


class Command(BaseCommand):
    help = 'Генерация тестовых пользователей'

    def add_arguments(self, parser):
        parser.add_argument('-c', '--count', type=int, default=5, help='Count users, max count is 30')
        parser.add_argument('-t', '--type', type=str, choices=ICONS_TYPES, default='initials', help='Type avatar')

    def handle(self, *args, **options):
        count = options.get('count') if options.get('count') < 30 else 30
        type_avatar = options.get('type')
        users = []

        for index in range(count):
            profile = fake.simple_profile()
            full_name = profile.get('name')
            avatar_name, avatar = upload_avatar(full_name, profile.get('sex').lower(), type_avatar)

            user = User(
                username=f'user_{index + 1}',
                full_name=full_name,
                phone=str(random.randint(79130000000, 79139999999)),
                is_email_verified=random.randint(0, 1),
                email=profile.get('mail'),
                avatar=File(avatar, avatar_name) if avatar else None
            )
            user.set_password('123456')
            users.append(user)

        if users:
            User.objects.bulk_create(users)

        self.stdout.write('Пользователи сгенерированы')
