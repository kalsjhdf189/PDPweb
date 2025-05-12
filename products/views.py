from django.shortcuts import render, redirect
from django.contrib import messages
from database import Connect, ProductGroup, ProductType, GroupProductType, Product, Partner, LegalAddress, PartnerType, Order, OrderProduct, Delivery, Payment, Delivery_method
from django.http import JsonResponse
import json
from datetime import datetime
from django.urls import reverse
import urllib.parse

def product_list(request):
    session = Connect.create_connection()
    product_groups = session.query(ProductGroup).all()
    for group in product_groups:
        group_types = session.query(GroupProductType).filter(GroupProductType.id_группа_продукции == group.id).all()
        group.product_types = [session.query(ProductType).get(group_type.id_тип_продукции) for group_type in group_types]
    session.close()
    return render(request, 'products/product_list.html', {'product_groups': product_groups})

def product_type_list(request, type_id):
    session = Connect.create_connection()
    product_type = session.query(ProductType).get(type_id)
    products = session.query(Product).filter(Product.id_тип == type_id).all()
    session.close()
    return render(request, 'products/product_type_list.html', {
        'product_type': product_type,
        'products': products
    })

def product_detail(request, product_id):
    session = Connect.create_connection()
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
    if 'partner_id' not in request.session:
        auth_url = reverse('auth')
        redirect_url = f"{auth_url}?{urllib.parse.urlencode({'next': 'checkout'})}"
        return redirect(redirect_url)

    session = Connect.create_connection()
    try:
        delivery_methods = session.query(Delivery_method).all()

        if request.method == 'POST':
            delivery_method_id = request.POST.get('delivery_method')
            comment = request.POST.get('comment')
            cart_data = request.POST.get('cart')
            индекс = request.POST.get('индекс')
            регион = request.POST.get('регион')
            город = request.POST.get('город')
            улица = request.POST.get('улица')
            дом = request.POST.get('дом')

            if not cart_data:
                messages.error(request, 'Корзина пуста!')
                return redirect('checkout')

            if not delivery_method_id:
                messages.error(request, 'Пожалуйста, выберите способ доставки!')
                return redirect('checkout')

            if not all([индекс, регион, город, улица, дом]):
                messages.error(request, 'Все поля адреса доставки должны быть заполнены!')
                return redirect('checkout')

            try:
                cart = json.loads(cart_data)
                if not cart:
                    messages.error(request, 'Корзина пуста!')
                    return redirect('checkout')

                partner = session.query(Partner).filter_by(id=request.session['partner_id']).first()
                if not partner:
                    messages.error(request, 'Партнёр не найден!')
                    return redirect('checkout')

                total_price = sum(float(item['price']) * item['quantity'] for item in cart)

                total_weight = 0
                for item in cart:
                    product = session.query(Product).filter_by(id=item['id']).first()
                    if product and product.Вес:
                        try:
                            weight = float(product.Вес.split()[0])
                            total_weight += weight * item['quantity']
                        except ValueError:
                            weight = 0

                delivery_method = session.query(Delivery_method).filter_by(id=delivery_method_id).first()
                if not delivery_method:
                    messages.error(request, 'Способ доставки не найден!')
                    return redirect('checkout')

                delivery_cost = delivery_method.Базовая_стоимость or 0.0
                if delivery_method.Стоимость_за_кг and total_weight > 0:
                    delivery_cost += delivery_method.Стоимость_за_кг * total_weight

                legal_address = LegalAddress(
                    Индекс=int(индекс) if индекс else None,
                    Регион=регион,
                    Город=город,
                    Улица=улица,
                    Дом=int(дом) if дом else None
                )
                session.add(legal_address)
                session.flush()

                payment = Payment(
                    Дата_оплаты=None,
                    Статус='Не оплачен',
                    Сумма=total_price + delivery_cost
                )
                session.add(payment)
                session.flush()

                delivery_status = 'Самовывоз' if delivery_method.Наименование == 'Самовывоз' else 'Ожидает отправки'
                delivery = Delivery(
                    id_способ_доставки=int(delivery_method_id),
                    id_юр_адрес=legal_address.id,
                    Статус=delivery_status,
                    Стоимость=delivery_cost
                )
                session.add(delivery)
                session.flush()

                order = Order(
                    Дата_создания=datetime.now(),
                    Статус='В обработке',
                    id_партнер=partner.id,
                    id_доставка=delivery.id,
                    id_оплата=payment.id,
                    Комментарий=comment,
                    id_сотрудник=None
                )
                session.add(order)
                session.commit()

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
                        Стоимость=float(item['price'])
                    )
                    session.add(order_product)

                session.commit()
                messages.success(request, 'Заказ успешно оформлен!')
                return redirect('personal_account')

            except Exception as e:
                session.rollback()
                messages.error(request, f'Ошибка при создании заказа: {str(e)}')
                return redirect('checkout')

        return render(request, 'products/checkout.html', {
            'delivery_methods': delivery_methods,
            'total_weight': 0
        })

    finally:
        session.close()

def calculate_delivery_cost(request):
    if request.method == 'POST':
        session = Connect.create_connection()
        try:
            data = json.loads(request.body)
            delivery_method_id = data.get('delivery_method_id')
            cart = data.get('cart', [])
            partner_id = request.session.get('partner_id')

            if not delivery_method_id or not partner_id:
                return JsonResponse({'error': 'Недостаточно данных'}, status=400)

            delivery_method = session.query(Delivery_method).filter_by(id=delivery_method_id).first()
            if not delivery_method:
                return JsonResponse({'error': 'Способ доставки не найден'}, status=404)

            total_weight = 0
            for item in cart:
                product = session.query(Product).filter_by(id=item['id']).first()
                if product and product.Вес:
                    try:
                        weight = float(product.Вес.split()[0])
                        total_weight += weight * item['quantity']
                    except ValueError:
                        weight = 0

            delivery_cost = delivery_method.Базовая_стоимость or 0.0
            if delivery_method.Стоимость_за_кг and total_weight > 0:
                delivery_cost += delivery_method.Стоимость_за_кг * total_weight

            return JsonResponse({'delivery_cost': delivery_cost})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        finally:
            session.close()
    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

def auth(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        session = Connect.create_connection()
        try:
            partner = session.query(Partner).filter_by(email=email, Пароль=password).first()
            if partner:
                request.session['partner_id'] = partner.id
                messages.success(request, 'Вход выполнен успешно!')
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('personal_account')
            else:
                messages.error(request, 'Неверный email или пароль!')
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    auth_url = reverse('auth')
                    redirect_url = f"{auth_url}?{urllib.parse.urlencode({'next': next_url})}"
                    return redirect(redirect_url)
                return redirect('auth')
        finally:
            session.close()
    
    next_url = request.GET.get('next', '')
    return render(request, 'products/auth.html', {'next': next_url})

def register(request):
    if request.method == 'POST':
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
            existing_partner_email = session.query(Partner).filter_by(email=email).first()
            if existing_partner_email:
                messages.error(request, 'Партнёр с таким email уже существует!')
                return redirect('register')

            existing_partner_inn = session.query(Partner).filter_by(ИНН=инн).first()
            if existing_partner_inn:
                messages.error(request, 'Партнёр с таким ИНН уже существует!')
                return redirect('register')

            if not all([индекс, регион, город, улица, дом]):
                messages.error(request, 'Все поля юридического адреса должны быть заполнены!')
                return redirect('register')

            legal_address = LegalAddress(
                Индекс=int(индекс) if индекс else None,
                Регион=регион,
                Город=город,
                Улица=улица,
                Дом=int(дом) if дом else None
            )
            session.add(legal_address)
            session.flush()

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
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                auth_url = reverse('auth')
                redirect_url = f"{auth_url}?{urllib.parse.urlencode({'next': next_url})}"
                return redirect(redirect_url)
            return redirect('auth')
        except Exception as e:
            session.rollback()
            messages.error(request, f'Ошибка при регистрации: {str(e)}')
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                register_url = reverse('register')
                redirect_url = f"{register_url}?{urllib.parse.urlencode({'next': next_url})}"
                return redirect(redirect_url)
            return redirect('auth')
        finally:
            session.close()

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
    if 'partner_id' not in request.session:
        messages.error(request, 'Пожалуйста, войдите в систему.')
        return redirect('auth')

    session = Connect.create_connection()
    try:
        partner = session.query(Partner).filter_by(id=request.session['partner_id']).first()

        current_orders = session.query(Order).filter(
            Order.id_партнер == partner.id,
            Order.Статус.in_(['В обработке', 'Принят', 'Согласован', 'В пути'])
        ).all()

        order_history = session.query(Order).filter(
            Order.id_партнер == partner.id,
            Order.Статус.in_(['Отменён', 'Завершён'])
        ).all()

        for order in current_orders + order_history:
            order.доставка = session.query(Delivery).get(order.id_доставка)
            order.оплата = session.query(Payment).get(order.id_оплата)
            if order.доставка:
                order.доставка.способ_доставки = session.query(Delivery_method).get(order.доставка.id_способ_доставки)
                order.доставка.юридический_адрес = session.query(LegalAddress).get(order.доставка.id_юр_адрес)
            # Вычисление subtotal для каждого заказа
            order.subtotal = sum(item.Стоимость * item.Количество for item in order.заказы_продукции)

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
            partner = session.query(Partner).filter_by(id=request.session['partner_id']).first()
            if not partner:
                messages.error(request, 'Партнёр не найден.')
                return redirect('personal_account')

            if not all([индекс, регион, город, улица, дом]):
                messages.error(request, 'Все поля юридического адреса должны быть заполнены!')
                return redirect('personal_account')

            partner.Наименование = наименование
            partner.ФИО_директора = фио_директора
            partner.Телефон = телефон
            partner.Места_продаж = места_продаж
            if пароль:
                partner.Пароль = пароль

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
        order = session.query(Order).filter_by(id=order_id).first()
        if not order:
            messages.error(request, 'Заказ не найден.')
            return redirect('personal_account')

        if order.id_партнер != request.session['partner_id']:
            messages.error(request, 'У вас нет доступа к этому заказу.')
            return redirect('personal_account')

        if order.Статус not in ['В обработке', 'Согласован', 'В пути']:
            messages.error(request, 'Этот заказ нельзя отменить.')
            return redirect('personal_account')

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