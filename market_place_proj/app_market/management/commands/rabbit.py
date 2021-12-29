import json
import logging
import pickle
import time

from django.core.management import BaseCommand
from django.db import IntegrityError, transaction
from django.db.models import F

import pika
import requests
from app_market.models import Cart, Catalog, Order, OrderDetail
from app_market.utils import CartService

from market_place_proj.settings import PAYMENT_HOST, RMQ_HOST


logging.basicConfig()
formatter = logging.Formatter('%(asctime)s.%(msecs)d %(process)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)
logger.propagate = False
stream = logging.StreamHandler()
stream.setFormatter(formatter)
file = logging.FileHandler(filename='rabbit.log', mode='w', encoding='UTF-8')
file.setFormatter(formatter)
stream.setLevel('INFO')
file.setLevel('INFO')
logger.addHandler(stream)
logger.addHandler(file)
logger.setLevel('INFO')


def validate_goods_count(cart):
    """функция проверяет достаточность товара для заказа"""

    messages = []
    for good in cart:
        if good.count > good.catalog.count:
            message = 'нехватает товара {seller} {good} {count} {catalog_count}'.format(
                seller=good.catalog.seller.title,
                good=good.catalog.good.title,
                count=good.count,
                catalog_count=good.catalog.count)
            logger.error(message)
            messages.append(message)
    if len(messages) > 0:
        return False, messages
    return True, None


def request_api(pay):
    """функция получает ответ от сервера"""
    try:
        response = requests.post(url=f'{PAYMENT_HOST}/api/pay/', json=pay, timeout=30)
        logger.info(response.status_code)
        if response.status_code not in [200, 201]:
            return
        data = response.json()
        data['status_code'] = response.status_code
        logger.info(data)
        return data
    except ConnectionError as E:
        logger.exception(exc_info=E, msg='Ошибка requests')


def teleportation_good_from_cart_to_order_detail(order: Order):
    """списание товара у продавца"""
    goods = OrderDetail.objects.filter(order_id=order.id).select_related(
        'cart', 'cart__catalog', 'cart__catalog__seller', 'cart__catalog__good')
    for good in goods:
        Catalog.objects.filter(pk=good.cart.catalog.pk).update(count=F('count') - good.cart.count)
        logger.info('перемещение товара {gg}, продавец: {ss}, количество {cc}'.format(
            gg=good.cart.catalog.good.title,
            ss=good.cart.catalog.seller.title,
            cc=good.cart.count
        ))


def create_order_detail(order: Order, cart: Cart.objects):
    """функция переносит товары из корзины в детали заказа"""
    try:
        # order.closed = True
        details = []
        for item in cart:
            if item.price_with_discount:
                sale_price = item.price_with_discount
            elif item.price_without_discount:
                sale_price = item.price_without_discount
            else:
                sale_price = item.catalog.price
            details.append(
                OrderDetail(
                    price=sale_price,
                    count=item.count,
                    cart_id=item.id,
                    order_id=order.pk,
                )
            )
        OrderDetail.objects.bulk_create(details)
        # очистим корзину
        Cart.objects.filter(user_id=order.user.pk, soft_delete=False).update(soft_delete=True)
        return True
    except Exception as E:
        logger.exception(exc_info=E, msg='Ошибка добавления товаров в заказ')


def callback(ch, method, properties, body: bytes):
    """
    Добавим через апи платёж
    """
    pay = pickle.loads(body)
    pay = json.loads(pay)
    pay['shop_token'] = 'megano'
    logger.info(f'send to api: {pay}')
    try:
        # получим корзину
        order = Order.objects.get(id=pay['order_id'])
        if not order:
            logger.error(f"попытка запросить несуществующий заказ с идентификатором {pay['order_id']}")
            return
        elif order.status == 'pay_success':
            pay['error'] = 'Заказ уже был оплачен. Повторная оплата невозможна'
            pay['status'] = 'error'
            raise IntegrityError('repeated payment is not possible')

        # создаём детали заказа
        cart, cart_amount_dict = CartService.get_goods_from_cart(user_id=order.user.pk)
        if not create_order_detail(order, cart):
            pay['error'] = 'Ошибка добавления товара из корзины в заказ'
            pay['status'] = 'error'
            raise IntegrityError('create detail error')

        with transaction.atomic():
            # валидируем количество товара
            validated_count, messages = validate_goods_count(cart)
            if not validated_count:
                pay['error'] = ', '.join(messages)
                pay['status'] = 'error'
                raise IntegrityError('goods count error')
            # обратимся к апи
            data = request_api(pay)
            if not data:
                pay['error'] = 'Ошибка получения данных от сервиса оплаты'
                pay['status'] = 'error'
                raise IntegrityError('request error')
            logger.info(f'request: {data}')
            pay.update(data)
            if pay['status'] == 'error':
                raise IntegrityError('Оплата завершилась неудачно')

            teleportation_good_from_cart_to_order_detail(order)
            Order.objects.filter(id=pay['order_id']).update(
                status='pay_success', response=json.dumps(pay, ensure_ascii=False))
            return
    except Exception as E:
        logger.info(pay)
        logger.exception(exc_info=E, msg='ошибка выполнения запроса')
    new_order = Order.objects.filter(id=pay['order_id'])
    logger.info(f'count {new_order.count()}')
    new_order.update(
        status=pay['status'], response=json.dumps(pay, ensure_ascii=False))
    logger.info(new_order)


class Command(BaseCommand):
    help = 'Обработка очереди платежей'

    def handle(self, *args, **options):
        """Запуск кролика в бесконечном цикле"""
        while True:
            try:
                logger.info(f'RMQ_HOST:{RMQ_HOST}')
                conn_params = pika.ConnectionParameters(RMQ_HOST)
                connection = pika.BlockingConnection(conn_params)
                channel = connection.channel()
                channel.queue_declare(queue='payment')
                channel.basic_consume(queue='payment', on_message_callback=callback, auto_ack=True)
                logger.info('Следуй за белым RabbitMQ')
                channel.start_consuming()
            except KeyboardInterrupt:
                logger.info('ехит')
                break
            time.sleep(5)
