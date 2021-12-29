import os
import random
import sys
import zipfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from app_market.models import Catalog, Seller


about_ru = """Миссия компании - в каждом доме - по печке
Каждой печке - по лавке
Каждой лавке - по ребёнку""",
about_en = """The company's mission is to have a stove in every house
Each pack has a bench
Each shop has a child"""

sellers = [
    dict(title_ru='Электро-Дом', title_en='Electro-House',
         delivery_ru='Доставка в любую точку мира голубиной почтой',
         money_ru='Вернем деньги, мамой клянусь',
         suppurt_ru='Окажем моральную поддержку, похлопаем по плечу, дружеские обнимашки',
         quality_ru='Быстро, дешево, качественно - любые два на выбор',
         phone_ru='Телефон милиции: 020\nСкорой помощи: 030\nПожарных: 010',
         address_ru='Москва, Третья улица Строителей, дом 25 офис 12',
         mail_ru='hello@skillbox.ru',
         delivery_en='Delivery to anywhere in the world by pigeon mail',
         money_en='We will return the money, I swear by my mother',
         suppurt_en='We will provide moral support, pat on the shoulder, friendly hugs',
         quality_en='Fast, cheap, high quality - any two to choose from',
         phone_en='Police phone number: 020\nAmbulance: 030\nFirefighters: 010',
         address_en='Moscow, Third street Builders, house 25 office 12',
         mail_en='hello@skillbox.ru',
         about_ru=about_ru, about_en=about_en),
    dict(title_ru='Книга-Фига', title_en='Book-Fico',
         delivery_ru='Доставка в любую точку мира с проводником скорого поезда РЖД',
         quality_ru='Быстро, дешево, качественно - любые два на выбор',
         suppurt_ru='Окажем моральную поддержку, похлопаем по плечу, дружеские обнимашки',
         money_ru='Вернем деньги, мамой клянусь',
         phone_ru='Телефон милиции: 020\nСкорой помощи: 030\nПожарных: 010',
         address_ru='Москва, Третья улица Строителей, дом 25 офис 12',
         mail_ru='hello@skillbox.ru',
         about_ru=about_ru, about_en=about_en,
         delivery_en='Delivery to anywhere in the world with a conductor of a fast Russian Railways train',
         quality_en='Fast, cheap, high quality - any two to choose from',
         suppurt_en='We will provide moral support, pat on the shoulder, friendly hugs',
         money_en='We will return the money, I swear by my mother',
         phone_en='Police phone number: 020\nAmbulance: 030\nFirefighters: 010',
         address_en='Moscow, Third street Builders, house 25 office 12',
         mail_en='hello@skillbox.ru'),
    dict(title_ru='Робо-Коробас', title_en='RoboBox',
         delivery_ru='Доставка в любую точку мира ракетами Калибр',
         quality_ru='Быстро, дешево, качественно - любые два на выбор',
         suppurt_ru='Окажем моральную поддержку, похлопаем по плечу, дружеские обнимашки',
         money_ru='Вернем деньги, мамой клянусь',
         phone_ru='Телефон милиции: 020\nСкорой помощи: 030\nПожарных: 010',
         address_ru='Москва, Третья улица Строителей, дом 25 офис 12',
         mail_ru='hello@skillbox.ru',
         delivery_en='Delivery to anywhere in the world by Caliber missiles',
         quality_en='Fast, cheap, high quality - any two to choose from',
         suppurt_en='We will provide moral support, pat on the shoulder, friendly hugs',
         money_en='We will return the money, I swear by my mother',
         phone_en='Police phone number: 020\nAmbulance: 030\nFirefighters: 010',
         address_en='Moscow, Third street Builders, house 25 office 12',
         mail_en='hello@skillbox.ru',
         about_ru=about_ru, about_en=about_en),
    dict(title_ru='Темная личность', title_en='Dark Personality',
         delivery_ru='Доставка в любую точку мира при помощи телепортации',
         quality_ru='Быстро, дешево, качественно - любые два на выбор',
         suppurt_ru='Окажем моральную поддержку, похлопаем по плечу, дружеские обнимашки',
         money_ru='Вернем деньги, мамой клянусь',
         phone_ru='Телефон милиции: 020\nСкорой помощи: 030\nПожарных: 010',
         address_ru='Москва, Третья улица Строителей, дом 25 офис 12',
         mail_ru='hello@skillbox.ru',
         delivery_en='Delivery to anywhere in the world by teleportation',
         quality_en='Fast, cheap, high quality - any two to choose from',
         suppurt_en='We will provide moral support, pat on the shoulder, friendly hugs',
         money_en='We will return the money, I swear by my mother',
         phone_en='Police phone number: 020\nAmbulance: 030\nFirefighters: 010',
         address_en='Moscow, Third street Builders, house 25 office 12',
         mail_en='hello@skillbox.ru',
         about_ru=about_ru, about_en=about_en),
    dict(title_ru='Цугундер', title_en='Zugunder',
         about_ru=about_ru, about_en=about_en,
         suppurt_ru='Окажем моральную поддержку, похлопаем по плечу, дружеские обнимашки',
         quality_ru='Быстро, дешево, качественно - любые два на выбор',
         money_ru='Вернем деньги из общака',
         phone_ru='Телефон милиции: 020\nСкорой помощи: 030\nПожарных: 010',
         address_ru='Москва, Третья улица Строителей, дом 25 офис 12',
         mail_ru='hello@skillbox.ru',
         suppurt_en='We will provide moral support, pat on the shoulder, friendly hugs',
         quality_en='Fast, cheap, high quality - any two to choose from',
         money_en='We will return the money from the general fund',
         phone_en='Police phone number: 020\nAmbulance: 030\nFirefighters: 010',
         address_en='Moscow, Third street Builders, house 25 office 12',
         mail_en='hello@skillbox.ru',
         delivery_en='Delivery to any area of the world using quadrocopters',
         delivery_ru='Доставка в любую зону мира при помощи квадрокоптеров'),
]

User = get_user_model()


class Command(BaseCommand):
    help = 'Генерация продавцов и их пользователей'

    def handle(self, *args, **options):
        User.objects.filter(username__in=[f'seller_{index + 1}' for index in range(5)]).delete()
        Catalog.objects.all().delete()
        Seller.objects.all().delete()
        path = (os.path.split(sys.argv[0])[0])
        zf = zipfile.ZipFile(os.path.join(path, 'app_market', 'management', 'commands', 'brands.zip'))
        zf.extractall(os.path.join(settings.MEDIA_ROOT, 'users'))
        if not os.path.exists(os.path.join(settings.MEDIA_ROOT, 'users')):
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'users'))
        for index, data in enumerate(sellers):
            filepath = f'brand_{index}.svg'
            seller = Seller.objects.create(title=data['title_ru'],
                                           title_ru=data['title_ru'],
                                           title_en=data['title_en'],
                                           about_info=data['about_ru'],
                                           about_info_ru=data['about_ru'],
                                           about_info_en=data['about_en'],
                                           icon=os.path.join('users', filepath),
                                           delivery_info=data['delivery_ru'],
                                           delivery_info_ru=data['delivery_ru'],
                                           delivery_info_en=data['delivery_en'],
                                           money_info=data['money_ru'],
                                           money_info_ru=data['money_ru'],
                                           money_info_en=data['money_en'],
                                           support_info=data['suppurt_ru'],
                                           support_info_ru=data['suppurt_ru'],
                                           support_info_en=data['suppurt_en'],
                                           quality_info=data['quality_ru'],
                                           quality_info_ru=data['quality_ru'],
                                           quality_info_en=data['quality_en'],
                                           phone_info=data['phone_ru'],
                                           phone_info_ru=data['phone_ru'],
                                           phone_info_en=data['phone_en'],
                                           address_info=data['address_ru'],
                                           address_info_ru=data['address_ru'],
                                           address_info_en=data['address_en'],
                                           mail_info=data['mail_ru'],
                                           mail_info_ru=data['mail_ru'],
                                           mail_info_en=data['mail_ru'],
                                           fb_info='www.vk.com',
                                           tw_info='www.vk.com',
                                           gg_info='www.vk.com',
                                           in_info='www.vk.com',
                                           pt_info='www.vk.com',
                                           ml_info='www.vk.com',
                                           )
            User.objects.create_user(
                username=f'seller_{index + 1}',
                password='123456',
                full_name=f'Директор магазина {data["title_ru"]}',
                phone=str(random.randint(79130000000, 79139999999)),
                is_email_verified=True,
                email='diplom_skillbox@mail.ru',
                avatar=os.path.join('users', filepath),
                seller=seller
            )
            print(index)
        print('продавцы готовы')
