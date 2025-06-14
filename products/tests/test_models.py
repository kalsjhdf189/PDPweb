import pytest
import json
from django.urls import reverse
from django.contrib.messages import get_messages
from database import Partner, LegalAddress, Order, Product, OrderProduct, Delivery, Delivery_method, Payment

pytestmark = pytest.mark.django_db

def test_auth_valid_credentials(django_client):
    """Тест-кейс №1: Авторизация пользователя с правильными данными."""
    # Предусловие: пользователь зарегистрирован
    legal_address = LegalAddress(
        Индекс=123456, Регион="Москва", Город="Москва", Улица="Ленина", Дом=10
    )
    partner = Partner(
        email="info@murmur.ru", Пароль="1234", Наименование="Test Partner",
        id_юр_адрес=legal_address.id, ИНН="1234567890", ФИО_директора="Иванов И.И.",
        Телефон="1234567890", Места_продаж="Москва", id_тип=1
    )
    with django_client.session.transaction():
        django_client.session['legal_address'] = legal_address.__dict__
        django_client.session['partner'] = partner.__dict__
        django_client.session.save()

    # Шаги воспроизведения
    response = django_client.post(reverse('auth'), {
        'email': 'info@murmur.ru',
        'password': '1234',
        'action': 'login'
    })

    # Проверка результатов
    assert response.status_code == 302
    assert response.url == reverse('personal_account')
    messages = [m.message for m in get_messages(response.wsgi_request)]
    assert 'Вход выполнен успешно!' in messages

def test_address_autocomplete(django_client, mocker):
    """Тест-кейс №2: Автодополнение адреса при регистрации."""
    # Мокаем запрос к DaData API
    mock_response = {
        'suggestions': [{
            'value': 'г Москва, ул Арбат, д 40',
            'data': {
                'postal_code': '123456',
                'region': 'Москва',
                'city': 'Москва',
                'street': 'Арбат',
                'house': '40'
            }
        }]
    }
    mocker.patch('requests.post', return_value=mocker.Mock(json=lambda: mock_response))

    # Шаги воспроизведения
    response = django_client.get(reverse('auth'))
    assert response.status_code == 200

    # Имитация регистрации с автодополнением адреса
    response = django_client.post(reverse('register'), {
        'address': 'Москва, Арбат 40',
        'наименование': 'Test Partner',
        'инн': '1234567890',
        'фио_директора': 'Иванов И.И.',
        'телефон': '1234567890',
        'email': 'test@example.com',
        'пароль': 'test123',
        'места_продаж': 'Москва',
        'индекс': '123456',
        'регион': 'Москва',
        'город': 'Москва',
        'улица': 'Арбат',
        'дом': '40',
        'тип_партнера': 1
    })

    # Проверка результатов
    assert response.status_code == 302
    assert LegalAddress.objects.filter(Улица='Арбат', Дом='40').exists()
    assert Partner.objects.filter(email='test@example.com').exists()

def test_cancel_order(django_client):
    """Тест-кейс №3: Отмена текущего заказа."""
    # Предусловие: пользователь авторизован, есть заказ
    legal_address = LegalAddress(
        Индекс=123456, Регион="Москва", Город="Москва", Улица="Ленина", Дом=10
    )
    partner = Partner(
        email="test@example.com", Пароль="test123", Наименование="Test Partner",
        id_юр_адрес=legal_address.id, ИНН="1234567890", ФИО_директора="Иванов И.И.",
        Телефон="1234567890", Места_продаж="Москва", id_тип=1
    )
    delivery_method = Delivery_method(Наименование="Курьер", Вместимость="10 кг", Базовая_стоимость=500.0, Стоимость_за_кг=50.0)
    delivery = Delivery(id_способ_доставки=delivery_method.id, id_юр_адрес=legal_address.id, Статус="В обработке", Стоимость=500.0)
    payment = Payment(Дата_оплаты="2025-01-01 10:00:00", Статус="Ожидает", Сумма=1000.0)
    order = Order(
        Дата_создания="2025-01-01 10:00:00", Статус="В обработке",
        id_партнер=partner.id, id_доставка=delivery.id, id_оплата=payment.id
    )
    with django_client.session.transaction():
        django_client.session['legal_address'] = legal_address.__dict__
        django_client.session['partner'] = partner.__dict__
        django_client.session['delivery_method'] = delivery_method.__dict__
        django_client.session['delivery'] = delivery.__dict__
        django_client.session['payment'] = payment.__dict__
        django_client.session['order'] = order.__dict__
        django_client.session.save()

    django_client.login(email='test@example.com', password='test123')

    # Шаги воспроизведения
    response = django_client.get(reverse('cancel_order', args=[order.id]))

    # Проверка результатов
    assert response.status_code == 302
    order = Order.objects.get(id=order.id)
    assert order.Статус == 'Отменён'
    messages = [m.message for m in get_messages(response.wsgi_request)]
    assert f'Заказ №{order.id} успешно отменён' in messages

def test_add_to_cart(django_client):
    """Тест-кейс №4: Добавление товара в корзину."""
    # Предусловие: есть товар
    product = Product(
        Наименование='Профессиональный бентонитовый наполнитель',
        Стоимость=100.0, id_тип=1
    )
    with django_client.session.transaction():
        django_client.session['product'] = product.__dict__
        django_client.session.save()

    # Шаги воспроизведения
    response = django_client.post(reverse('add_to_cart'), {
        'product_id': product.id,
        'quantity': 1
    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    # Проверка результатов
    assert response.status_code == 200
    cart = django_client.session.get('cart', [])
    assert any(item['id'] == str(product.id) for item in cart)

def test_checkout_order(django_client):
    """Тест-кейс №5: Оформление заказа."""
    # Предусловие: пользователь авторизован, товар в корзине
    legal_address = LegalAddress(
        Индекс=123456, Регион="Москва", Город="Москва", Улица="Ленина", Дом=10
    )
    partner = Partner(
        email="test@example.com", Пароль="test123", Наименование="Test Partner",
        id_юр_адрес=legal_address.id, ИНН="1234567890", ФИО_директора="Иванов И.И.",
        Телефон="1234567890", Места_продаж="Москва", id_тип=1
    )
    product = Product(
        Наименование='Test Product', Стоимость=100.0, id_тип=1
    )
    delivery_method = Delivery_method(Наименование="Курьер", Вместимость="10 кг", Базовая_стоимость=500.0, Стоимость_за_кг=50.0)
    delivery = Delivery(id_способ_доставки=delivery_method.id, id_юр_адрес=legal_address.id, Статус="В обработке", Стоимость=500.0)
    payment = Payment(Дата_оплаты="2025-01-01 10:00:00", Статус="Ожидает", Сумма=1000.0)
    with django_client.session.transaction():
        django_client.session['legal_address'] = legal_address.__dict__
        django_client.session['partner'] = partner.__dict__
        django_client.session['product'] = product.__dict__
        django_client.session['delivery_method'] = delivery_method.__dict__
        django_client.session['delivery'] = delivery.__dict__
        django_client.session['payment'] = payment.__dict__
        django_client.session['cart'] = [{'id': str(product.id), 'quantity': 1, 'price': 100.0}]
        django_client.session.save()

    django_client.login(email='test@example.com', password='test123')

    # Шаги воспроизведения
    response = django_client.post(reverse('checkout'), {
        'payment_method': 'Банковский перевод',
        'comment': 'Хорошо упакуйте',
        'cart': json.dumps(django_client.session['cart'])
    })

    # Проверка результатов
    assert response.status_code == 302
    assert response.url == reverse('personal_account')
    messages = [m.message for m in get_messages(response.wsgi_request)]
    assert 'Заказ успешно оформлен!' in messages
    assert Order.objects.filter(Комментарий='Хорошо упакуйте').exists()
    assert OrderProduct.objects.filter(id_продукции=product.id, Количество=1).exists()