from django.shortcuts import render
from database import Connect, ProductGroup, ProductType, GroupProductType, Product

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