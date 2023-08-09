from .serializers import ClientSerializer, EventSerializer
from boto3.dynamodb.conditions import Key
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from datetime import datetime
from uuid import uuid4
import uuid
import boto3

# Configuración de DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
client_table = dynamodb.Table('clients')
event_table = dynamodb.Table('events')


class ListClientsView(APIView):
    def get(self, request):
        response = client_table.scan()
        clients = response.get('Items', [])
        return Response(clients)


class ClientCreateAPiView(APIView):
    def post(self, request):
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Crear el cliente en la tabla
                client_table.put_item(Item=serializer.validated_data)
                
                # Obtener el client_id del cliente recién creado
                client_id = serializer.validated_data.get('client_id')
                
                # Obtener el session_id desde el request
                session_id = request.data.get('session_id')
                
                # Si el session_id está presente, actualizamos los eventos
                if session_id:
                    # Realiza un query para obtener todos los eventos con ese session_id
                    response = event_table.query(
                        IndexName='session_id-index',
                        KeyConditionExpression=Key('session_id').eq(session_id)
                    )
                    events = response.get('Items', [])

                    # Actualiza cada evento para añadir el client_id
                    for event in events:
                        event['client_id'] = client_id
                        event_table.put_item(Item=event)

                return Response({"message": "Cliente creado exitosamente."}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class ClientDetailView(APIView):

    def get(self, request, client_id):
        response = client_table.get_item(Key={'client_id': client_id})
        client = response.get('Item', None)
        if client:
            return Response(client)
        return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, client_id):
        # Recuperamos el cliente actual para confirmar que existe
        response = client_table.get_item(Key={'client_id': client_id})
        client = response.get('Item', None)
        if not client:
            return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        # Fusionamos la data actual con la nueva data
        update_data = {**client, **request.data}

        serializer = ClientSerializer(data=update_data)
        if serializer.is_valid():
            try:
                client_table.put_item(Item=serializer.validated_data)
                return Response({"message": "Cliente actualizado exitosamente."}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, client_id):
        # Verificamos que el cliente exista antes de intentar eliminarlo
        response = client_table.get_item(Key={'client_id': client_id})
        client = response.get('Item', None)
        if not client:
            return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        try:
            client_table.delete_item(Key={'client_id': client_id})
            return Response({"message": "Cliente eliminado exitosamente."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventListApiView(APIView):
    def get(self, request):
        response = event_table.scan()
        events = response.get('Items', [])
        return Response(events)


class EventCreateAPIView(APIView):
    def post(self, request):
        # Genera un UUID si no viene en el request
        if 'session_id' not in request.data:
            request.data['session_id'] = str(uuid4())  # Convertir UUID a string aquí
        if 'event_id' not in request.data:
            request.data['event_id'] = str(uuid4())  # Convertir UUID a string aquí

        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            try:
                event_data = serializer.validated_data
                # Convertir el timestamp a formato ISO 8601
                event_data['timestamp'] = datetime.now().isoformat()  # Añadir timestamp y convertir a string

                # Convertir event_id y session_id a strings si son de tipo UUID
                if isinstance(event_data.get('event_id'), uuid.UUID):
                    event_data['event_id'] = str(event_data['event_id'])
                if isinstance(event_data.get('session_id'), uuid.UUID):
                    event_data['session_id'] = str(event_data['session_id'])

                event_table.put_item(Item=event_data)
                return Response({"message": "Evento creado exitosamente."}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EventDetailView(APIView):
    def get(self, request, event_id, session_id):
        response = event_table.get_item(Key={'event_id': str(event_id), 'session_id': str(session_id)})
        event = response.get('Item', None)
        if event:
            return Response(event)
        return Response({"error": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, event_id, session_id):
    # Obtener el evento
        response = event_table.get_item(Key={'event_id': str(event_id), 'session_id': str(session_id)})
        event = response.get('Item', None)

        if not event:
            return Response({"error": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        # Actualizar el evento
        for key, value in request.data.items():
            event[key] = value

        # Guardar el evento actualizado
        event_table.put_item(Item=event)

        return Response({"message": "Evento actualizado exitosamente."}, status=status.HTTP_200_OK)
    
    def delete(self, request, event_id, session_id):
    # Intentar eliminar el evento. Si el evento no existe, DynamoDB no arrojará un error.
        event_table.delete_item(Key={'event_id': str(event_id), 'session_id': str(session_id)})

        return Response({"message": "Evento eliminado exitosamente."}, status=status.HTTP_204_NO_CONTENT)
    





