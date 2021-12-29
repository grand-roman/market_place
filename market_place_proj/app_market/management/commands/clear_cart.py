from django.core.management import BaseCommand

from app_market.models import Cart


class Command(BaseCommand):
    help = 'Очистка корзины'

    def handle(self, *args, **options):
        Cart.objects.all().delete()
        self.stdout.write("Корзина очищена")
