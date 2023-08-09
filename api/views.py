# Importaciones necesarias
from .serializers import ClientSerializer, EventSerializer
from boto3.dynamodb.conditions import Key
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from datetime import datetime
from uuid import uuid4
import uuid
import boto3

# Configuración inicial de DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
client_table = dynamodb.Table('clients')
event_table = dynamodb.Table('events')

# Vista para listar todos los clientes
class ListClientsView(APIView):
    def get(self, request):
        # Realizar un escaneo completo de la tabla de clientes
        response = client_table.scan() # lo mismo que eventos, no realiar a menos que sea necesario
        clients = response.get('Items', [])
        return Response(clients)

# Vista para crear un nuevo cliente
class ClientCreateAPiView(APIView):
    def post(self, request):
        # Serializar los datos recibidos
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

# Vista para obtener, actualizar o eliminar un cliente específico
class ClientDetailView(APIView):
    def get(self, request, client_id):
        # Obtener un cliente específico por su client_id
        response = client_table.get_item(Key={'client_id': client_id})
        client = response.get('Item', None)
        if client:
            return Response(client)
        return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, client_id):
        # Actualizar un cliente específico por su client_id
        response = client_table.get_item(Key={'client_id': client_id})
        client = response.get('Item', None)
        if not client:
            return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        update_data = {**client, **request.data}
        serializer = ClientSerializer(data=update_data)
        if serializer.is_valid():
            client_table.put_item(Item=serializer.validated_data)
            return Response({"message": "Cliente actualizado exitosamente."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, client_id):
        # Eliminar un cliente específico por su client_id
        client_table.delete_item(Key={'client_id': client_id})
        return Response({"message": "Cliente eliminado exitosamente."}, status=status.HTTP_200_OK)

# Vista para listar todos los eventos
class EventListApiView(APIView):
    def get(self, request):
        # Realizar un escaneo completo de la tabla de eventos
        response = event_table.scan() # no llamar a menos que sea necesario, de preferencia agregar condicional para solo llamar los mas recientes o importantes, scan es costoso  si la tabla tiene muuchos datos
        events = response.get('Items', [])
        return Response(events)

# Vista para crear un nuevo evento
class EventCreateAPIView(APIView):
    def post(self, request):
        # Generar UUIDs para session_id y event_id si no se proporcionan
        if 'session_id' not in request.data:
            request.data['session_id'] = str(uuid4())
        if 'event_id' not in request.data:
            request.data['event_id'] = str(uuid4())
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            event_data = serializer.validated_data
            event_data['timestamp'] = datetime.now().isoformat()
            if isinstance(event_data.get('event_id'), uuid.UUID):
                event_data['event_id'] = str(event_data['event_id'])
            if isinstance(event_data.get('session_id'), uuid.UUID):
                event_data['session_id'] = str(event_data['session_id'])
            event_table.put_item(Item=event_data)
            return Response({"message": "Evento creado exitosamente."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Vista para obtener, actualizar o eliminar un evento específico
class EventDetailView(APIView):
    def get(self, request, event_id, session_id):
        # Obtener un evento específico por su event_id y session_id
        response = event_table.get_item(Key={'event_id': str(event_id), 'session_id': str(session_id)})
        event = response.get('Item', None)
        if event:
            return Response(event)
        return Response({"error": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, event_id, session_id):
        # Actualizar un evento específico por su event_id y session_id
        response = event_table.get_item(Key={'event_id': str(event_id), 'session_id': str(session_id)})
        event = response.get('Item', None)
        if not event:
            return Response({"error": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        for key, value in request.data.items():
            event[key] = value
        event_table.put_item(Item=event)
        return Response({"message": "Evento actualizado exitosamente."}, status=status.HTTP_200_OK)

    def delete(self, request, event_id, session_id):
        # Eliminar un evento específico por su event_id y session_id
        event_table.delete_item(Key={'event_id': str(event_id), 'session_id': str(session_id)})
        return Response({"message": "Evento eliminado exitosamente."}, status=status.HTTP_204_NO_CONTENT)
    


#vista de eventos por client_id y session_id

class ClientEventsView(APIView):
    def get(self, request, client_id):
        # Realiza una consulta en la tabla de eventos usando el GSI de client_id
        response = event_table.query(
            IndexName='client_id-index',  # Asegúrate de que este sea el nombre correcto de tu GSI
            KeyConditionExpression=Key('client_id').eq(client_id)
        )
        
        events = response.get('Items', [])
        
        if not events:
            return Response({"error": "No se encontraron eventos para el cliente."}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(events)
    
class SessionEventsApiView(APIView):
    def get(self, request, session_id):
        # Realiza una consulta en el GSI basado en session_id
        response = event_table.query(
            IndexName='session_id-index',
            KeyConditionExpression=Key('session_id').eq(session_id)
        )
        events = response.get('Items', [])
        
        if not events:
            return Response({"error": "No se encontraron eventos para la sesión proporcionada."}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(events)




