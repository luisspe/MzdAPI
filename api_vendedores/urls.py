from django.urls import path
from .views import VendedorCreateAPIView,ListVendedoresView

urlpatterns = [
    path('', ListVendedoresView.as_view(), name='vendedor-list'),
    path('create/', VendedorCreateAPIView.as_view(), name='vendedor-create'),
    # Agrega aquí más rutas si necesitas más funcionalidades para los vendedores
]