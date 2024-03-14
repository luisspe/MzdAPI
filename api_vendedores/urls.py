from django.urls import path
from .views import VendedorCreateAPIView,ListVendedoresView, VendedorByEmailAPIView

urlpatterns = [
    path('', ListVendedoresView.as_view(), name='vendedor-list'),
    path('create/', VendedorCreateAPIView.as_view(), name='vendedor-create'),
    path('vendedor/<str:email>/', VendedorByEmailAPIView.as_view(), name='vendedor-by-email'),
    # Agrega aquí más rutas si necesitas más funcionalidades para los vendedores
]