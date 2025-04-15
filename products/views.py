from django.shortcuts import render, redirect
from django.contrib import messages
from database import Connect, ProductGroup, ProductType, GroupProductType, Product, Partner, LegalAddress, PartnerType, Order, OrderProduct
from django.http import JsonResponse
import json
from datetime import datetime
from django.urls import reverse
import urllib.parse

def product_list(request):
    session = Connect.create_connection()
    # Получаем все группы продукции
    product_groups = session.query(ProductGroup).all()
    # Для каждой группы получаем связанные типы продукции
    for group in product_groups:
        # Находим все записи в таблице группа_тип_продукции, связанные с этой группой
        group_types = session.query(GroupProductType).filter(GroupProductType.id_группа_продукции == group.id).all()
        # Извлекаем типы продукции для этой группы
        group.product_types = [session.query(ProductType).get(group_type.id_тип_продукции) for group_type in group_types]
    session.close()
    return render(request, 'products/product_list.html', {'product_groups': product_groups})

def product_type_list(request, type_id):
    session = Connect.create_connection()
    # Получаем тип продукции по ID
    product_type = session.query(ProductType).get(type_id)
    # Получаем все продукты, связанные с этим типом
    products = session.query(Product).filter(Product.id_тип == type_id).all()
    session.close()
    return render(request, 'products/product_type_list.html', {
        'product_type': product_type,
        'products': products
    })

def product_detail(request, product_id):
    session = Connect.create_connection()
    # Получаем продукт по ID
    product = session.query(Product).get(product_id)
    session.close()
    return render(request, 'products/product_detail.html', {'product': product})

def about(request):
    return render(request, 'products/about.html')

def contacts(request):
    return render(request, 'products/contacts.html')

def cart(request):
    return render(request, 'products/cart.html')

def checkout(request):
    # Проверяем, авторизован ли пользователь
    if 'partner_id' not in request.session:
        # Перенаправляем на страницу авторизации с параметром next как query-параметр
        auth_url = reverse('auth')
        redirect_url = f"{auth_url}?{urllib.parse.urlencode({'next': 'checkout'})}"
        return redirect(redirect_url)

    if request.method == 'POST':
        # Получаем данные из формы
        payment_method = request.POST.get('payment_method')
        comment = request.POST.get('comment')
        cart_data = request.POST.get('cart')  # Данные корзины в формате JSON

        # Проверяем, что корзина не пуста
        if not cart_data:
            messages.error(request, 'Корзина пуста!')
            return redirect('checkout')

        # Проверяем, выбран ли способ оплаты
        if not payment_method:
            messages.error(request, 'Пожалуйста, выберите способ оплаты!')
            return redirect('checkout')

        # Инициализируем session как None
        session = None
        try:
            cart = json.loads(cart_data)
            if not cart:
                messages.error(request, 'Корзина пуста!')
                return redirect('checkout')

            # Создаём подключение к базе данных
            session = Connect.create_connection()

            # Получаем партнёра из сессии
            partner = session.query(Partner).filter_by(id=request.session['partner_id']).first()
            if not partner:
                messages.error(request, 'Партнёр не найден!')
                return redirect('checkout')

            # Вычисляем общую сумму
            total_price = sum(float(item['price']) * item['quantity'] for item in cart)

            # Создаём заказ
            order = Order(
                Дата_создания=datetime.now(),
                Статус='В обработке',  # Устанавливаем статус по умолчанию
                id_партнер=partner.id,
                Способ_оплаты=payment_method,
                Общая_сумма=total_price,
                Комментарий=comment,
                id_сотрудник=None  # Если сотрудник не участвует в создании заказа
            )
            session.add(order)
            session.commit()

            # Создаём элементы заказа
            for item in cart:
                product = session.query(Product).filter_by(id=item['id']).first()
                if not product:
                    session.rollback()
                    messages.error(request, f'Продукт с ID {item["id"]} не найден!')
                    return redirect('checkout')

                order_product = OrderProduct(
                    id_заказа=order.id,
                    id_продукции=product.id,
                    Количество=item['quantity'],
                    Стоимость=float(item['price'])  # Сохраняем цену на момент заказа
                )
                session.add(order_product)

            # Подтверждаем транзакцию
            session.commit()

            # Успешное создание заказа
            messages.success(request, 'Заказ успешно оформлен!')
            return redirect('personal_account')

        except Exception as e:
            if session:
                session.rollback()
                session.close()
            messages.error(request, f'Ошибка при создании заказа: {str(e)}')
            return redirect('checkout')

        finally:
            if session:
                session.close()

    return render(request, 'products/checkout.html')

def auth(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        session = Connect.create_connection()
        try:
            partner = session.query(Partner).filter_by(email=email, Пароль=password).first()
            if partner:
                # Успешная авторизация
                request.session['partner_id'] = partner.id
                messages.success(request, 'Вход выполнен успешно!')
                # Проверяем параметр next в GET или POST
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('personal_account')
            else:
                messages.error(request, 'Неверный email или пароль!')
                # Сохраняем параметр next при ошибке авторизации
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    auth_url = reverse('auth')
                    redirect_url = f"{auth_url}?{urllib.parse.urlencode({'next': next_url})}"
                    return redirect(redirect_url)
                return redirect('auth')
        finally:
            session.close()
    
    # При GET-запросе передаём параметр next в контекст
    next_url = request.GET.get('next', '')
    return render(request, 'products/auth.html', {'next': next_url})

def register(request):
    if request.method == 'POST':
        # Получаем данные из формы
        наименование = request.POST.get('наименование')
        инн = request.POST.get('инн')
        фио_директора = request.POST.get('фио_директора')
        телефон = request.POST.get('телефон')
        email = request.POST.get('email')
        пароль = request.POST.get('пароль')
        места_продаж = request.POST.get('места_продаж')
        индекс = request.POST.get('индекс')
        регион = request.POST.get('регион')
        город = request.POST.get('город')
        улица = request.POST.get('улица')
        дом = request.POST.get('дом')
        тип_партнера_id = request.POST.get('тип_партнера')

        session = Connect.create_connection()
        try:
            # Проверяем, существует ли партнёр с таким email
            existing_partner_email = session.query(Partner).filter_by(email=email).first()
            if existing_partner_email:
                messages.error(request, 'Партнёр с таким email уже существует!')
                return redirect('register')

            # Проверяем, существует ли партнёр с таким ИНН
            existing_partner_inn = session.query(Partner).filter_by(ИНН=инн).first()
            if existing_partner_inn:
                messages.error(request, 'Партнёр с таким ИНН уже существует!')
                return redirect('register')

            # Проверяем, что все поля адреса заполнены
            if not all([индекс, регион, город, улица, дом]):
                messages.error(request, 'Все поля юридического адреса должны быть заполнены!')
                return redirect('register')

            # Создаём юридический адрес
            legal_address = LegalAddress(
                Индекс=int(индекс) if индекс else None,
                Регион=регион,
                Город=город,
                Улица=улица,
                Дом=int(дом) if дом else None
            )
            session.add(legal_address)
            session.flush()  # Сохраняем адрес, чтобы получить его id

            # Создаём нового партнёра
            new_partner = Partner(
                id_юр_адрес=legal_address.id,
                Наименование=наименование,
                ИНН=инн,
                ФИО_директора=фио_директора,
                id_тип=int(тип_партнера_id),
                Телефон=телефон,
                email=email,
                Места_продаж=места_продаж,
                Пароль=пароль
            )
            session.add(new_partner)
            session.commit()

            messages.success(request, 'Регистрация выполнена успешно! Теперь вы можете войти.')
            # Передаём параметр next, если он есть
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                auth_url = reverse('auth')
                redirect_url = f"{auth_url}?{urllib.parse.urlencode({'next': next_url})}"
                return redirect(redirect_url)
            return redirect('auth')
        except Exception as e:
            session.rollback()
            messages.error(request, f'Ошибка при регистрации: {str(e)}')
            # Передаём параметр next при ошибке
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                register_url = reverse('register')
                redirect_url = f"{register_url}?{urllib.parse.urlencode({'next': next_url})}"
                return redirect(redirect_url)
            return redirect('auth')
        finally:
            session.close()

    # При GET-запросе возвращаем страницу авторизации с формой регистрации
    session = Connect.create_connection()
    try:
        partner_types = session.query(PartnerType).all()
        next_url = request.GET.get('next', '')
        return render(request, 'products/auth.html', {
            'partner_types': partner_types,
            'show_register_form': True,
            'next': next_url
        })
    finally:
        session.close()

def personal_account(request):
    # Проверяем, авторизован ли пользователь
    if 'partner_id' not in request.session:
        messages.error(request, 'Пожалуйста, войдите в систему.')
        return redirect('auth')

    session = Connect.create_connection()
    try:
        # Получаем данные партнёра
        partner = session.query(Partner).filter_by(id=request.session['partner_id']).first()

        # Получаем текущие заказы (статусы: В обработке, Согласован, В пути)
        current_orders = session.query(Order).filter(
            Order.id_партнер == partner.id,
            Order.Статус.in_(['В обработке', 'Согласован', 'В пути'])
        ).all()

        # Получаем историю заказов (статусы: Отменён, Завершён)
        order_history = session.query(Order).filter(
            Order.id_партнер == partner.id,
            Order.Статус.in_(['Отменён', 'Завершён'])
        ).all()

        return render(request, 'products/personal_account.html', {
            'partner': partner,
            'current_orders': current_orders,
            'order_history': order_history
        })
    finally:
        session.close()

def update_personal_data(request):
    if 'partner_id' not in request.session:
        messages.error(request, 'Пожалуйста, войдите в систему.')
        return redirect('auth')

    if request.method == 'POST':
        # Получаем данные из формы
        наименование = request.POST.get('наименование')
        фио_директора = request.POST.get('фио_директора')
        телефон = request.POST.get('телефон')
        места_продаж = request.POST.get('места_продаж')
        пароль = request.POST.get('пароль')
        индекс = request.POST.get('индекс')
        регион = request.POST.get('регион')
        город = request.POST.get('город')
        улица = request.POST.get('улица')
        дом = request.POST.get('дом')

        session = Connect.create_connection()
        try:
            # Находим партнёра
            partner = session.query(Partner).filter_by(id=request.session['partner_id']).first()
            if not partner:
                messages.error(request, 'Партнёр не найден.')
                return redirect('personal_account')

            # Проверяем, что все поля адреса заполнены
            if not all([индекс, регион, город, улица, дом]):
                messages.error(request, 'Все поля юридического адреса должны быть заполнены!')
                return redirect('personal_account')

            # Обновляем данные партнёра
            partner.Наименование = наименование
            partner.ФИО_директора = фио_директора
            partner.Телефон = телефон
            partner.Места_продаж = места_продаж
            if пароль:
                partner.Пароль = пароль

            # Обновляем юридический адрес
            legal_address = partner.юридический_адрес
            legal_address.Индекс = int(индекс) if индекс else None
            legal_address.Регион = регион
            legal_address.Город = город
            legal_address.Улица = улица
            legal_address.Дом = int(дом) if дом else None

            session.commit()
            messages.success(request, 'Данные успешно обновлены!')
            return redirect('personal_account')
        except Exception as e:
            session.rollback()
            messages.error(request, f'Ошибка при обновлении данных: {str(e)}')
            return redirect('personal_account')
        finally:
            session.close()

    return redirect('personal_account')

def cancel_order(request, order_id):
    if 'partner_id' not in request.session:
        messages.error(request, 'Пожалуйста, войдите в систему.')
        return redirect('auth')

    session = Connect.create_connection()
    try:
        # Находим заказ
        order = session.query(Order).filter_by(id=order_id).first()
        if not order:
            messages.error(request, 'Заказ не найден.')
            return redirect('personal_account')

        # Проверяем, принадлежит ли заказ текущему партнёру
        if order.id_партнер != request.session['partner_id']:
            messages.error(request, 'У вас нет доступа к этому заказу.')
            return redirect('personal_account')

        # Проверяем, можно ли отменить заказ (только если статус "В обработке", "Согласован" или "В пути")
        if order.Статус not in ['В обработке', 'Согласован', 'В пути']:
            messages.error(request, 'Этот заказ нельзя отменить.')
            return redirect('personal_account')

        # Меняем статус заказа на "Отменён"
        order.Статус = 'Отменён'
        session.commit()
        messages.success(request, f'Заказ №{order_id} успешно отменён.')
        return redirect('personal_account')
    except Exception as e:
        session.rollback()
        messages.error(request, f'Ошибка при отмене заказа: {str(e)}')
        return redirect('personal_account')
    finally:
        session.close()