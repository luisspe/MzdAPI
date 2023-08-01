from django.urls import path
from .views import (
    ListClientsView, 
    ClientCreateAPiView, 
    ClientDetailView,
    EventListApiView,
    EventCreateAPIView,
    EventDetailView,
    
)

urlpatterns = [
    # Rutas para clientes
    path('clients/', ListClientsView.as_view(), name='list_clients'),
    path('clients/create/', ClientCreateAPiView.as_view(), name='create_client'),
    path('clients/<str:client_id>/', ClientDetailView.as_view(), name='detail_client'),

    # Rutas para eventos
    path('events/', EventListApiView.as_view(), name='list_events'),
    path('events/create/', EventCreateAPIView.as_view(), name='create_event'),
    path('events/<str:event_id>/<str:session_id>/', EventDetailView.as_view(), name='detail_event'),
  
]