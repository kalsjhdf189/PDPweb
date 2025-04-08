from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('type/<int:type_id>/', views.product_type_list, name='product_type_list'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
]