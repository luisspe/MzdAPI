from django.urls import path
from .views import ClientCreateAPiView, ClientUpdateView, ClientDetailView, ClientDeleteView,EventCreateAPIView

urlpatterns = [
  path('clients/', ClientCreateAPiView.as_view(), name='client-list-create'),
  path('client/<int:pk>/', ClientDetailView.as_view(), name='client-detail'),
  path('client/<int:pk>/update/', ClientUpdateView.as_view(), name='client-update'),
  path('client/<int:pk>/delete/', ClientDeleteView.as_view(), name='client-delete'),
  # Vista para crear un nuevo evento
  path('events/', EventCreateAPIView.as_view(), name='event-create'),
]
