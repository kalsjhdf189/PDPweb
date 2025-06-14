import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from database import Connect, Partner, ProductType, Product, Order, Payment, Delivery, Delivery_method
from unittest.mock import patch

class TestCases(TestCase):
    def setUp(self):
        self.session = Connect.create_connection()
        self.client = Client()

    def tearDown(self):
        self.session.close()

    def test_0001_authorization_success(self):
        response = self.client.get(reverse('auth'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('auth'), {
            'email': 'info@murmur.ru',
            'password': '1234'
        }, follow=True)

        self.assertRedirects(response, reverse('personal_account'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), 'Вход выполнен успешно!')
        self.assertIn('partner_id', self.client.session)
        
    def test_0004_add_to_cart(self):
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)

        product_type = self.session.query(ProductType).filter_by(Наименование='Комкующиеся бентонитовые наполнители').first()
        response = self.client.get(reverse('product_type_list', args=[product_type.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['product_type'].Наименование, 'Комкующиеся бентонитовые наполнители')

        product = self.session.query(Product).filter_by(Наименование='Профессиональный бентонитовый наполнитель').first()
        response = self.client.get(reverse('product_detail', args=[product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['product'].Наименование, 'Профессиональный бентонитовый наполнитель')

        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)

    def test_0005_checkout(self):
        self.client.post(reverse('auth'), {
            'email': 'info@murmur.ru',
            'password': '1234'
        })

        product = self.session.query(Product).filter_by(Наименование='Профессиональный бентонитовый наполнитель').first()

        cart = [{
            'id': str(product.id),
            'name': product.Наименование,
            'price': float(product.Стоимость),
            'image': product.Изображение,
            'quantity': 1
        }]

        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('checkout'), {
            'cart': json.dumps(cart),
            'delivery_method': 3,
            'comment': 'Хорошо упакуйте',
            'индекс': '123456',
            'регион': 'Москва',
            'город': 'Москва',
            'улица': 'Тестовая',
            'дом': '1'
        }, follow=True)

        self.assertRedirects(response, reverse('personal_account'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), 'Заказ успешно оформлен!')

        new_order = self.session.query(Order).filter_by(Комментарий='Хорошо упакуйте').first()
        self.assertIsNotNone(new_order)
        
        payment = self.session.query(Payment).filter_by(id=new_order.id_оплата).first()
        delivery = self.session.query(Delivery).filter_by(id=new_order.id_доставка).first()
        delivery_method = self.session.query(Delivery_method).filter_by(id=delivery.id_способ_доставки).first()
        self.assertIsNotNone(payment)
        self.assertIsNotNone(delivery)

        self.assertEqual(payment.Сумма, 425.0)
        self.assertEqual(delivery.id_способ_доставки, delivery_method.id)