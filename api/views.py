from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework import permissions
from .models import Client, Event
from .serializers import ClientSerializer, EventSerializer
from django.http import Http404

class ClientCreateAPiView(generics.CreateAPIView):

    serializer_class = ClientSerializer

    def create(self, request, *args, **kwargs):
        # Procesar los datos enviados por la plataforma y guardar el nuevo cliente
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Respuesta personalizada
        response_data = {
            "message": "client created.",
            "data": serializer.data
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

class ClientDetailView(generics.RetrieveAPIView):
    serializer_class = ClientSerializer

    def get_object(self):
        # Obtener un cliente específico de la base de datos
        cliente_id = self.kwargs['pk']
        try:
            client = Client.objects.get(pk=cliente_id)
        except Client.DoesNotExist:
            raise Http404("El cliente no existe.")
        return client

    def retrieve(self, request, *args, **kwargs):
        # Obtener el cliente y su representación serializada
        client = self.get_object()
        serializer = self.get_serializer(client)

        # Respuesta personalizada
        response_data = {
            "message": "Client found.",
            "data": serializer.data
        }

        return Response(response_data, status=status.HTTP_200_OK)
   
class ClientUpdateView(generics.UpdateAPIView):
    serializer_class = ClientSerializer

    def get_object(self):
        # Obtener el cliente existente
        cliente_id = self.kwargs['pk']
        try:
            client = Client.objects.get(pk=cliente_id)
        except Client.DoesNotExist:
            raise Http404("Client doesn't exist.")
        return client

    def update(self, request, *args, **kwargs):
        # Obtener el cliente existente
        instance = self.get_object()

        # Procesar los datos enviados por el cliente y actualizar el cliente
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Respuesta personalizada
        response_data = {
            "message": "El client has been updated.",
            "data": serializer.data
        }

        return Response(response_data, status=status.HTTP_200_OK)
    

class ClientDeleteView(generics.DestroyAPIView):
    serializer_class = ClientSerializer

    def get_object(self):
        # Obtener el cliente existente
        cliente_id = self.kwargs['pk']
        try:
            client = Client.objects.get(pk=cliente_id)
        except Client.DoesNotExist:
            raise Http404("Client doesn't exist.")
        return client

    def destroy(self, request, *args, **kwargs):
        # Obtener el cliente existente
        client = self.get_object()

        #Eliminar Cliente
        client.delete()

        # Respuesta personalizada
        response_data = {
            "message": "client has been deleted.",
            
        }

        return Response(response_data, status=status.HTTP_204_NO_CONTENT)
    

class EventCreateAPIView(generics.CreateAPIView):
    serializer_class = EventSerializer

    def create(self, request, *args, **kwargs):
        # Procesar los datos enviados por la plataforma y guardar el nuevo evento
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Respuesta personalizada
        response_data = {
            "message": "Event created.",
            "data": serializer.data
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class EventDetailView(generics.RetrieveAPIView):
    serializer_class = EventSerializer

    def get_object(self):
        # Obtener un evento específico de la base de datos
        event_id = self.kwargs['pk']
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise Http404("El evento no existe.")
        return event

    def retrieve(self, request, *args, **kwargs):
        # Obtener el evento y su representación serializada
        event = self.get_object()
        serializer = self.get_serializer(event)

        # Respuesta personalizada
        response_data = {
            "message": "Event found.",
            "data": serializer.data
        }

        return Response(response_data, status=status.HTTP_200_OK)


class EventUpdateView(generics.UpdateAPIView):
    serializer_class = EventSerializer

    def get_object(self):
        # Obtener el evento existente
        event_id = self.kwargs['pk']
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise Http404("Event doesn't exist.")
        return event

    def update(self, request, *args, **kwargs):
        # Obtener el evento existente
        instance = self.get_object()

        # Procesar los datos enviados por el cliente y actualizar el evento
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Respuesta personalizada
        response_data = {
            "message": "El evento has been updated.",
            "data": serializer.data
        }

        return Response(response_data, status=status.HTTP_200_OK)


class EventDeleteView(generics.DestroyAPIView):
    serializer_class = EventSerializer

    def get_object(self):
        # Obtener el evento existente
        event_id = self.kwargs['pk']
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise Http404("Event doesn't exist.")
        return event

    def destroy(self, request, *args, **kwargs):
        # Obtener el evento existente
        event = self.get_object()

        # Eliminar evento
        event.delete()

        # Respuesta personalizada
        response_data = {
            "message": "Event has been deleted.",
        }

        return Response(response_data, status=status.HTTP_204_NO_CONTENT)