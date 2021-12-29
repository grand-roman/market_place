from django.core.management import BaseCommand

from app_market.utils import PayOrderService


class Command(BaseCommand):
    help = 'Обработка очереди платежей'

    def handle(self, *args, **options):
        order_id = options['order_id']
        order = PayOrderService.get_order_by_id(order_id)
        if not order:
            print(f'Заказ с идентификатором {order_id} несуществует')
            return
        elif order.status == 'pay_success':
            print(f'Заказ с идентификатором {order_id} уже оплачен. Повторная оплата невозможна')
            return
        PayOrderService.pay_order(order_id)
        print(f'Заказ {order_id} отправлен в очередь для оплаты')

    def add_arguments(self, parser):
        parser.add_argument(
            '-id', type=int, dest='order_id', help='идентификатор для добавления заказа в очередь')
        parser.add_argument(
            '-card', type=str, dest='card', help='номер карты оплаты')
