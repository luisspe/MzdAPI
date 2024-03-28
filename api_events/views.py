# Importaciones necesarias
from .serializers import  EventSerializer
from boto3.dynamodb.conditions import Key
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from datetime import datetime
from uuid import uuid4, UUID
from botocore.exceptions import ClientError
import uuid
import boto3
import pytz


# Función para validar si un valor es un UUID válido
def is_valid_uuid(val):
    try:
        UUID(str(val))
        return True
    except ValueError:
        return False

# Configuración inicial de DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
client_table = dynamodb.Table('clients')
event_table = dynamodb.Table('eventsv2')



# Vista para listar todos los eventos
class EventListApiView(APIView):
    """
    View for listing all events.
    Supports:
    - GET: Fetches all events or, preferably, a filtered set based on conditions.
    """

    def scan_events(self, filter_condition=None):
        """Performs a scan on the event table, with optional filter condition."""
        scan_kwargs = {}
        if filter_condition:
            scan_kwargs['FilterExpression'] = filter_condition
        return event_table.scan(**scan_kwargs)

    def get(self, request):
        """Handles GET requests to fetch all or filtered events."""
        # For better performance, consider adding a filter condition instead of scanning all records
        # e.g., filtering for recent or important events
        response = self.scan_events()
        events = response.get('Items', [])
        return Response(events)

# Vista para crear un nuevo evento
class EventCreateAPIView(APIView):
    """
    View to create a new event.
    Supports:
    - POST: Creates a new event record.
    """

    def generate_ids(self, request):
        """Generates session_id and event_id if not provided."""
        if ('event_source' in request.data and request.data['event_source'] != 'website'):
            request.data['session_id'] = "12000000-0000-0000-0000-000000000000"
        elif 'session_id' not in request.data:
            request.data['session_id'] = str(uuid4())
        if 'event_id' not in request.data:
            request.data['event_id'] = str(uuid4())

    def post(self, request):
        """Handles POST requests to create a new event."""
        try:
            self.generate_ids(request)
            serializer = EventSerializer(data=request.data)
            if serializer.is_valid():
                event_data = serializer.validated_data
                mexico_tz = pytz.timezone('America/Mexico_City')
                event_data['timestamp'] = datetime.now(mexico_tz).strftime('%Y-%m-%d %H:%M:%S %Z%z')
                event_table.put_item(Item=event_data)
                # Modified to include the event_id in the response
                return Response({
                    "message": "Evento creado exitosamente.",
                    "event_id": request.data['event_id']  # Return the event_id
                }, status=status.HTTP_201_CREATED)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = {
                'ProvisionedThroughputExceededException': "Se ha excedido la capacidad provisionada. Por favor, inténtalo de nuevo más tarde.",
                'ResourceNotFoundException': "La tabla no fue encontrada.",
                'ConditionalCheckFailedException': "La condición especificada no se cumplió.",
                'ValidationException': "Hubo un problema con los datos de entrada."
            }.get(error_code, "Ocurrió un error al acceder a DynamoDB.")
            return Response({"error": error_message}, status=getattr(status, f'HTTP_{error_code}_INTERNAL_SERVER_ERROR', status.HTTP_500_INTERNAL_SERVER_ERROR))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Vista para obtener, actualizar o eliminar un evento específico
class EventDetailView(APIView):
    """
    View to retrieve, update, or delete a specific event.
    Supports:
    - GET: Retrieve a specific event by event_id and session_id.
    - PUT: Update a specific event by event_id and session_id.
    - DELETE: Delete a specific event by event_id and session_id.
    """
    
    def get_event(self, event_id, session_id):
        """Helper method to fetch an event."""
        response = event_table.get_item(Key={'event_id': str(event_id), 'session_id': str(session_id)})
        return response.get('Item', None)

    def get(self, request, event_id, session_id):
        """Handles GET requests to retrieve a specific event."""
        event = self.get_event(event_id, session_id)
        if event:
            return Response(event)
        return Response({"error": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, event_id, session_id):
        """Handles PUT requests to update a specific event."""
        event = self.get_event(event_id, session_id)
        if not event:
            return Response({"error": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        for key, value in request.data.items():
            event[key] = value
        event_table.put_item(Item=event)
        return Response({"message": "Evento actualizado exitosamente."}, status=status.HTTP_200_OK)

    def delete(self, request, event_id, session_id):
        """Handles DELETE requests to delete a specific event."""
        event_table.delete_item(Key={'event_id': str(event_id), 'session_id': str(session_id)})
        return Response({"message": "Evento eliminado exitosamente."}, status=status.HTTP_204_NO_CONTENT)
    

class EventByIdDetailView(APIView):
    """
    View to retrieve a specific event by its event_id.
    Supports:
    - GET: Retrieve a specific event by event_id.
    """

    def get_event(self, event_id):
        """
        Helper method to fetch an event based on event_id.
        :param event_id: The ID of the event to retrieve.
        :return: The event data, or None if not found.
        """
        response = event_table.get_item(Key={'event_id': str(event_id)})
        return response.get('Item', None)
    
    def get(self, request, event_id):
        """
        Handles GET requests to retrieve a specific event.
        :param request: The request object.
        :param event_id: The ID of the event to retrieve.
        :return: The event data, or a 404 error if not found.
        """
        event = self.get_event(event_id)
        if event:
            return Response(event)
        return Response({"error": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, event_id):
        """
        Handles PUT requests to update a specific event.
        :param request: The request object.
        :param event_id: The ID of the event to update.
        :return: Updated event data, or a 404 error if not found.
        """
        event = self.get_event(event_id)
        if not event:
            return Response({"error": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        for key, value in request.data.items():
            event[key] = value
        event_table.put_item(Item=event)
        return Response({"message": "Evento actualizado exitosamente."}, status=status.HTTP_200_OK)

    def delete(self, request, event_id):
        """
        Handles DELETE requests to delete a specific event.
        :param request: The request object.
        :param event_id: The ID of the event to delete.
        :return: Success message, or a 404 error if not found.
        """
        event = self.get_event(event_id)
        if not event:
            return Response({"error": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        event_table.delete_item(Key={'event_id': str(event_id)})
        return Response({"message": "Evento eliminado exitosamente."}, status=status.HTTP_204_NO_CONTENT)


    
class SessionEventsApiView(APIView):
    """
    View for listing all events associated with a specific session_id.
    Supports:
    - GET: Retrieve events linked to the provided session_id.
    """

    def get(self, request, session_id):
        """Handles GET requests to retrieve events based on session_id."""
        # Query the GSI based on session_id
        response = event_table.query(
            IndexName='session_id-index',
            KeyConditionExpression=Key('session_id').eq(session_id)
        )
        events = response.get('Items', [])
        
        if not events:
            return Response({"error": "No se encontraron eventos para la sesión proporcionada."}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(events)

class TodaysVisitsApiView(APIView):
    """
    View to list all visit registration events for the current day.
    Supports:
    - GET: Retrieve today's visit registration events.
    """

    def get(self, request):
        """Handles GET requests to retrieve today's visit registration events."""
        # Set the timezone for Mexico City
        mexico_tz = pytz.timezone('America/Mexico_City')
        # Get the current date in that timezone
        today = datetime.now(mexico_tz).strftime('%Y-%m-%d')
        
        # Query the table for today's visit registration events
        response = event_table.query(
            IndexName='event_type-timestamp-index',
            KeyConditionExpression='event_type = :etype AND begins_with(#ts, :today)',
            ExpressionAttributeNames={
                '#ts': 'timestamp',
            },
            ExpressionAttributeValues={
                ':today': today,
                ':etype': 'visit_registration',
            }
        )

        events = response.get('Items', [])
        return Response(events)

