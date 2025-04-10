from django.shortcuts import render, redirect
from django.contrib import messages
from database import Connect, ProductGroup, ProductType, GroupProductType, Product, Partner, LegalAddress, PartnerType
from django.http import JsonResponse

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
                return redirect('product_list')
            else:
                messages.error(request, 'Неверный email или пароль!')
                return redirect('auth')
        finally:
            session.close()
    
    return render(request, 'products/auth.html')

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
            # Проверяем, существует ли уже партнёр с таким email
            existing_partner = session.query(Partner).filter_by(email=email).first()
            if existing_partner:
                messages.error(request, 'Партнёр с таким email уже существует!')
                return redirect('auth')

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
            return redirect('auth')
        except Exception as e:
            session.rollback()
            messages.error(request, f'Ошибка при регистрации: {str(e)}')
            return redirect('auth')
        finally:
            session.close()

    # При GET-запросе возвращаем страницу авторизации с формой регистрации
    session = Connect.create_connection()
    try:
        partner_types = session.query(PartnerType).all()
        return render(request, 'products/auth.html', {'partner_types': partner_types, 'show_register_form': True})
    finally:
        session.close()