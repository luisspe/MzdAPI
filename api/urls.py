from django.urls import path
from .views import (
    ListClientsView, 
    ClientCreateAPiView, 
    ClientDetailView,
    EventListApiView,
    EventCreateAPIView,
    EventDetailView,
    ClientEventsView,
    SessionEventsApiView,
    TodaysVisitsApiView,
    ClientQueryByEmailAPIView,
    EventByIdDetailView
    
)

urlpatterns = [
    # Rutas para clientes
    path('clients/', ListClientsView.as_view(), name='list_clients'),
    path('clients/create/', ClientCreateAPiView.as_view(), name='create_client'),
    path('clients/<str:client_id>/', ClientDetailView.as_view(), name='detail_client'),
    path('clients/query/<str:email>/', ClientQueryByEmailAPIView.as_view(), name='client-query-by-email'),

    # Rutas para eventos
    path('events/', EventListApiView.as_view(), name='list_events'),
    path('events/create/', EventCreateAPIView.as_view(), name='create_event'),
    
    path('event/<str:event_id>/', EventByIdDetailView.as_view(), name='event-by-id-detail'),

    # Rutas para clientes - eventos 
    path('client/<str:client_id>/events/', ClientEventsView.as_view(), name='client-events'),
    path('session/<str:session_id>/events/', SessionEventsApiView.as_view(), name='session-events'),
    path('events/today-visits/', TodaysVisitsApiView.as_view(), name='today_visits_events'),
    
]

