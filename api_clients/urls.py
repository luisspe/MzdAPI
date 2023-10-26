from django.urls import path
from .views import (
    ListClientsView, 
    ClientCreateAPiView, 
    ClientDetailView,
    ClientQueryByEmailAPIView,
    ClientEventsView,
   
)

urlpatterns = [
    # Rutas para clientes
    path('', ListClientsView.as_view(), name='list_clients'),
    path('create/', ClientCreateAPiView.as_view(), name='create_client'),
    path('<str:client_id>/', ClientDetailView.as_view(), name='detail_client'),
    path('query/<str:email>/', ClientQueryByEmailAPIView.as_view(), name='client-query-by-email'),
    path('<str:client_id>/events/', ClientEventsView.as_view(), name='client-events'),
   
]

