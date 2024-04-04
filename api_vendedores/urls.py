from django.urls import path
from .views import VendedorCreateAPIView,ListVendedoresView, VendedorByEmailAPIView, VendedorByIdAPIView

urlpatterns = [
    path('', ListVendedoresView.as_view(), name='vendedor-list'),
    path('create/', VendedorCreateAPIView.as_view(), name='vendedor-create'),
    path('vendedor/<str:email>/', VendedorByEmailAPIView.as_view(), name='vendedor-by-email'),
    path('<str:vendedor_id>/', VendedorByIdAPIView.as_view(), name='vendedor-by-id'),
    
]