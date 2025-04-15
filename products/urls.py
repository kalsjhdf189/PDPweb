from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('type/<int:type_id>/', views.product_type_list, name='product_type_list'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('auth/', views.auth, name='auth'),
    path('register/', views.register, name='register'),
    path('personal-account/', views.personal_account, name='personal_account'),
    path('update-personal-data/', views.update_personal_data, name='update_personal_data'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('logout/', LogoutView.as_view(next_page='auth'), name='logout'),
]