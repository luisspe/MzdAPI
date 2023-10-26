from django.urls import path
from .views import (
    
    EventListApiView,
    EventCreateAPIView,
    EventDetailView,
    ClientEventsView,
    SessionEventsApiView,
    TodaysVisitsApiView,
   
    EventByIdDetailView
    
)

urlpatterns = [
    # Rutas para clientess
    # Rutas para eventos
    path('events/', EventListApiView.as_view(), name='list_events'),
    path('events/create/', EventCreateAPIView.as_view(), name='create_event'),
    
    path('event/<str:event_id>/', EventByIdDetailView.as_view(), name='event-by-id-detail'),

   
    path('session/<str:session_id>/events/', SessionEventsApiView.as_view(), name='session-events'),
    path('events/today-visits/', TodaysVisitsApiView.as_view(), name='today_visits_events'),
    


     # Rutas para clientes - eventos 
    path('client/<str:client_id>/events/', ClientEventsView.as_view(), name='client-events'),
]

