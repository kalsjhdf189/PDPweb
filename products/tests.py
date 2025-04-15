import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from database import Connect, Partner, ProductType, Product, Order
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

    def test_0002_address_autocomplete(self):
        mock_dadata_response = {
            'suggestions': [
                {
                    'value': 'г Москва, ул Арбат, д 40',
                    'data': {
                        'postal_code': '101000',
                        'region': 'Москва',
                        'city': 'Москва',
                        'street': 'ул Арбат',
                        'house': '40'
                    }
                }
            ]
        }

        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = mock_dadata_response
            mock_post.return_value.status_code = 200

            response = self.client.get(reverse('auth'))
            self.assertEqual(response.status_code, 200)

            response = self.client.get(reverse('register'))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['show_register_form'])

            response = self.client.post(reverse('register'), {
                'наименование': 'Уникальная компания',
                'инн': '123456789099',
                'фио_директора': 'Тестов Тест Тестович',
                'телефон': '79991234599',
                'email': 'unique@murmur.ru',
                'пароль': '4321',
                'места_продаж': 'Москва',
                'тип_партнера': 1,
                'address': 'г Москва, ул Арбат, д 40',
                'индекс': '101000',
                'регион': 'Москва',
                'город': 'Москва',
                'улица': 'ул Арбат',
                'дом': '40'
            }, follow=True)

            self.assertEqual(response.status_code, 200)
            messages_list = list(messages.get_messages(response.wsgi_request))
            self.assertEqual(len(messages_list), 1)
            self.assertEqual(str(messages_list[0]), 'Регистрация выполнена успешно! Теперь вы можете войти.')

            new_partner = self.session.query(Partner).filter_by(email='unique@murmur.ru').first()
            self.assertIsNotNone(new_partner)
            self.assertEqual(new_partner.юридический_адрес.Регион, 'Москва')
            self.assertEqual(new_partner.юридический_адрес.Улица, 'ул Арбат')
            self.assertEqual(new_partner.юридический_адрес.Дом, 40)

    def test_0003_cancel_order(self):
        partner = self.session.query(Partner).filter_by(email='info@murmur.ru').first()
        self.assertIsNotNone(partner)
        self.client.post(reverse('auth'), {
            'email': 'info@murmur.ru',
            'password': '1234'
        })

        order = self.session.query(Order).filter_by(id=3, id_партнер=partner.id).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.Статус, 'В обработке')

        response = self.client.get(reverse('personal_account'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(o.id == 3 for o in response.context['current_orders']))

        response = self.client.post(reverse('cancel_order', args=[3]), follow=True)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), 'Заказ №3 успешно отменён.')

        updated_order = self.session.query(Order).get(3)
        self.session.commit()
        self.assertEqual(updated_order.Статус, 'Отменён')

        response = self.client.get(reverse('personal_account'))
        self.assertTrue(any(o.id == 3 for o in response.context['order_history']))

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
            'price': product.Стоимость,
            'image': product.Изображение,
            'quantity': 1
        }]

        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('checkout'), {
            'cart': json.dumps(cart),
            'payment_method': 'Банковский перевод',
            'comment': 'Хорошо упакуйте'
        }, follow=True)

        self.assertRedirects(response, reverse('personal_account'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), 'Заказ успешно оформлен!')

        new_order = self.session.query(Order).filter_by(Комментарий='Хорошо упакуйте').first()
        self.assertIsNotNone(new_order)
        self.assertEqual(new_order.Способ_оплаты, 'Банковский перевод')
        self.assertEqual(new_order.Общая_сумма, 250.0)