from django.urls import path
from .views import (
    EventListApiView,
    EventCreateAPIView,
    SessionEventsApiView,
    TodaysVisitsApiView,
    EventByIdDetailView
    
)

urlpatterns = [
    
    # Rutas para eventos
    path('', EventListApiView.as_view(), name='list_events'),
    path('create/', EventCreateAPIView.as_view(), name='create_event'),
    path('event/<str:event_id>/', EventByIdDetailView.as_view(), name='event-by-id-detail'),
    path('session/<str:session_id>/events/', SessionEventsApiView.as_view(), name='session-events'),
    path('today-visits/', TodaysVisitsApiView.as_view(), name='today_visits_events'),
     # Rutas para clientes - eventos 
    
]

