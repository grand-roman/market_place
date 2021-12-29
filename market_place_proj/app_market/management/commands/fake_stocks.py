import random

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from app_market.models import Stock
from faker import Faker


User = get_user_model()
faker = Faker()

links = [
    r'https://ic.pics.livejournal.com/globolife/59791984/315463/315463_original.jpg',
    r'https://placepic.ru/wp-content/uploads/2018/12/raskraska_novogodnie_otkritki19.jpg',
    r'https://www.sdnjom.ru/uploads/posts/2017-04/1492247442_pozdravitelnaya-otkrytka-retro-s-novym-godom.jpg',
    r'https://iralebedeva.ru/images/zarubin_9bb.jpg',
    r'https://www.culture.ru/storage/images/3a1deaeebf2da8d9bdba55428bc325a0/fe29b8478d9ff9ff17cbdc7ae289662d.jpeg',
    r'http://img.crazys.info/files/pics/2015.12/1451271473_1.jpg',
    r'https://i.pinimg.com/736x/78/75/db/7875db7cf19d45c1181368df5eddb39b--winter-fun-christmas-photos.jpg'
]

title_ru = [
    r'Празднуй !', r'Поздравляй !', r'Отдыхай !', r'Твори добро !', r'Пора в отпуск !', r'Скоро Новый год!',
    r'Пора всё потратить!'
]

title_en = [
    'celebrate !', 'congratulations !', 'rest!', 'do good!', "it's time to go on vacation!",
    "the New Year is coming soon!",
    "Spur all to spend!"
]

content_ru = [
    r'31 декабря — это день, когда календарь отрывается по полной!',
    r'В жизни мужчины бывает три периода — когда он верит в Деда Мороза, когда не верит, и когда он сам Дед Мороз! ',
    r'В новогоднюю ночь все желания имеют особую силу',
    r'В Новый год я видел счастливых людей — и трезвых среди них не было',
    r'В следующем году обещаю вести себя примерно… Примерно, как в этом',
    r'Вниманию пользователей программы «Жизнь»: доступно обновление «2022». '
    r'Обновление будет установлено автоматически 31 декабря в 00.00 час. Спасибо, что вы с нами!',
    r'Год близится к концу, пора решить, во что нарядиться для ночи с 31 декабря на 9 января.'
]

content_en = [
    r"December 31 is the day when the calendar comes off in full!",
    r"There are three periods in a man's life — when he believes in Santa Claus, when he does not believe, and when "
    r"he is Santa Claus himself! ",
    r"On New Year's Eve, all wishes have a special power",
    r"In the New Year I saw happy people — and there were no sober ones among them",
    r"Next year I promise to behave approximately… Approximately, as in this ",
    r"To the attention of users of the program 'Life'': the update '2022'' is available. The update will be installed "
    r"automatically on December 31 at 00.00. Thank you for being with us!",
    r"The year is coming to an end, it's time to decide what to dress up for the night from December 31 to January 9."
]


class Command(BaseCommand):
    help = 'Генерация тестовых акций'

    def handle(self, *args, **options):
        options.setdefault('interactive', False)

        stocks = []
        for i in range(len(links)):
            stocks.append(Stock(
                title=faker.text(max_nb_chars=100),
                content=content_ru,
                content_ru=content_ru[i],
                content_en=content_en[i],
                title_ru=title_ru[i],
                title_en=title_en[i],
                is_active=True,
                image_link=links[i],
                sort=random.randint(100, 1000)
            ))

        Stock.objects.bulk_create(stocks)
        self.stdout.write("Акции сгенерированы")
