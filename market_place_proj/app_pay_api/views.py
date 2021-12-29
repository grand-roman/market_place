import datetime
import random
import time

from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from app_pay_api.serializers import PaySerialier
from rest_framework.views import APIView


"""
Реа*лизуйте сервис фиктивной оплаты. Этот сервис должен содержать один метод ― «Оплатить заказ».
В качестве параметра принимает три значения: номер заказа, номер карты, сумма к оплате.
Логика работы сервиса из ТЗ: «Если введённый номер чётный и не заканчивается на 0,
то оплата подтверждается. Если введённый номер нечётный и заканчивается на 0, то сервис
генерирует случайную ошибку оплаты».
После подтверждения или ошибки обработчик должен установить соответствующий статус оплаты заказу.
"""

exceptions = [_('We not like number 0'),
              _('You have not money'),
              _('Problem on the Sun'),
              _('Account block'),
              _('Account arrested'),
              _('Account does not exist'), ]


class PayApiView(APIView):
    """
    API оплаты
    """

    @csrf_exempt
    def post(self, request):
        """имитация работы платёжной системы"""
        self.request.data['created_at'] = datetime.datetime.utcnow()
        card: str = request.data['card']
        if card.endswith(('2', '4', '6', '8')):
            request.data['status'] = 'pay_success'
        else:
            request.data['status'] = 'error'
            request.data['error'] = random.choice(exceptions)

        serializer = PaySerialier(data=self.request.data)
        if serializer.is_valid():
            # имитация задержки при обращении к стороннему апи
            time.sleep(1)
            return JsonResponse(serializer.data)
        else:
            print(serializer.errors)
