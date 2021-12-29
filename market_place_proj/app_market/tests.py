from django.test import TestCase


class TestSale(TestCase):
    fixtures = ['test_data/sale/discounts.json']

    @classmethod
    def setUpTestData(cls):
        cls.create_fixture()
        cls.response = cls.client.get('catalog/sale')

    def test_discount_variants_calculate(self):
        for item in self.response.context['sale']:
            if item.discount.variants == 'Percent':
                self.assertEqual(item.good.discounted_price, item.good.price * item.good.discount)
            elif item.discount.variants == 'Sum':
                self.assertEqual(item.good.discounted_price, sum(item.good.price, item.good.discount))
            elif item.discount.variants == 'Fixed':
                self.assertEqual(item.discounted_price, item.good.discount)
