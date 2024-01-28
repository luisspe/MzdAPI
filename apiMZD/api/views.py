# Importaciones necesarias
from .serializers import ClientSerializer, EventSerializer
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

# Vista para listar todos los clientes
class ListClientsView(APIView):
    def get(self, request):
        """
        Handles GET requests to list all clients with pagination.

        Query Parameters:
        - last_evaluated_key: The last client ID from the previous page; used for pagination.

        Responses:
        - 200 OK: Returns a page of clients along with a token for the next page.
        - 500 Internal Server Error: Unexpected server error.
        """
        # Obtain pagination token if provided
        last_evaluated_key = request.GET.get('last_evaluated_key')

        # Initial configuration for the query
        scan_kwargs = {
            'Limit': 100  # Limit to 100 records per page, adjust as needed
        }

        # Use pagination token if provided
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = {'client_id': last_evaluated_key}

        try:
            # Perform a paginated scan on the clients table
            response = client_table.scan(**scan_kwargs)

            # Obtain the pagination token for the next page
            next_page_token = response.get('LastEvaluatedKey')

            # Prepare the response data
            data = {
                'clients': response.get('Items', []),
                'next_page_token': next_page_token
            }

            return Response(data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Vista para crear un nuevo cliente
class ClientCreateAPiView(APIView):
    def post(self, request):
        """
        Handles POST requests to create a new client.

        Request Body:
        - All fields required by the ClientSerializer.

        Responses:
        - 201 Created: Client was successfully created.
        - 400 Bad Request: Invalid data was supplied.
        - 404 Not Found: The table was not found.
        - 500 Internal Server Error: Unexpected server error.
        """
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Create the client in the table
                client_table.put_item(Item=serializer.validated_data)
                
                # Get the client_id of the newly created client
                client_id = serializer.validated_data.get('client_id')
                
                # Get the session_id from the request
                session_id = request.data.get('session_id')
                
                # If the session_id is present, update the events
                if session_id:
                    # Query to get all events with that session_id
                    response = event_table.query(
                        IndexName='session_id-index',
                        KeyConditionExpression=Key('session_id').eq(session_id)
                    )
                    events = response.get('Items', [])

                    # Update each event to add the client_id
                    for event in events:
                        event['client_id'] = client_id
                        event_table.put_item(Item=event)

                return Response({"message": "Cliente creado exitosamente."}, status=status.HTTP_201_CREATED)
            
            except ClientError as e:
                error_code = e.response['Error']['Code']
                return self.handle_client_error(error_code)
            
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def handle_client_error(self, error_code):
        """
        Handles known client errors from DynamoDB.

        Arguments:
        - error_code: The error code string from DynamoDB.

        Returns:
        - A Django Response object with a suitable error message and status code.
        """
        error_messages = {
            'ProvisionedThroughputExceededException': ("Se ha excedido la capacidad provisionada. "
                                                       "Por favor, inténtalo de nuevo más tarde."),
            'ResourceNotFoundException': "La tabla no fue encontrada.",
            'ConditionalCheckFailedException': "La condición especificada no se cumplió.",
            'ValidationException': "Hubo un problema con los datos de entrada."
        }
        error_message = error_messages.get(error_code, "Ocurrió un error al acceder a DynamoDB.")
        status_codes = {
            'ProvisionedThroughputExceededException': status.HTTP_503_SERVICE_UNAVAILABLE,
            'ResourceNotFoundException': status.HTTP_404_NOT_FOUND,
            'ConditionalCheckFailedException': status.HTTP_400_BAD_REQUEST,
            'ValidationException': status.HTTP_400_BAD_REQUEST
        }
        status_code = status_codes.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"error": error_message}, status=status_code)
    


class ClientDetailView(APIView):
    """
    Handles the retrieval, update, and deletion of a specific client based on client_id.
    """

    def get(self, request, client_id):
        """
        Retrieves a specific client by client_id.

        Responses:
        - 200 OK: Client was successfully retrieved.
        - 404 Not Found: Client was not found.
        """
        client = self.get_client(client_id)
        if client:
            return Response(client)
        return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, client_id):
        """
        Updates a specific client by client_id with the provided data.

        Responses:
        - 200 OK: Client was successfully updated.
        - 400 Bad Request: Invalid data was supplied.
        - 404 Not Found: Client was not found.
        """
        client = self.get_client(client_id)
        if not client:
            return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        update_data = {**client, **request.data}
        serializer = ClientSerializer(data=update_data)
        if serializer.is_valid():
            client_table.put_item(Item=serializer.validated_data)
            return Response({"message": "Cliente actualizado exitosamente."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client(self, client_id):
        """
        Helper method to retrieve a client by client_id.

        Returns:
        - The client data if found, otherwise None.
        """
        response = client_table.get_item(Key={'client_id': client_id})
        return response.get('Item', None)

    def delete(self, request, client_id):
        # Eliminar un cliente específico por su client_id
        client_table.delete_item(Key={'client_id': client_id})
        return Response({"message": "Cliente eliminado exitosamente."}, status=status.HTTP_200_OK)
    

class ClientQueryByEmailAPIView(APIView):
    """
    View for querying a client based on email.
    Supports:
    - GET: Fetches the client details based on email.
    """

    def query_client_by_email(self, email):
        """Performs a query on the database using the email."""
        return client_table.query(
            IndexName='email-index',  # Assuming you have a secondary index called 'email-index'
            KeyConditionExpression='email = :email_val',
            ExpressionAttributeValues={
                ':email_val': email
            }
        )

    def get(self, request, email):
        """Handles GET requests to fetch client details using email."""
        try:
            response = self.query_client_by_email(email)
            clients = response.get('Items', [])
            
            if clients:
                return Response(clients[0], status=status.HTTP_200_OK)  # Returns the first matching client
            else:
                return Response({"message": "No se encontraron clientes con ese correo electrónico"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            request.data['session_id'] = "00000000-0000-0000-0000-000000000000"
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
                return Response({"message": "Evento creado exitosamente."}, status=status.HTTP_201_CREATED)
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

#vista de eventos por client_id y session_id
class ClientEventsView(APIView):
    """
    View for listing all events associated with a specific client_id.
    Supports:
    - GET: Retrieve events with pagination.
    """

    def get(self, request, client_id):
        """Handles GET requests to retrieve events."""
        # Fetch pagination token if provided
        last_evaluated_key = request.GET.get('last_evaluated_key')
        
        # Initial configuration for the query
        query_kwargs = {
            'IndexName': 'client_id-index',
            'KeyConditionExpression': Key('client_id').eq(client_id),
            'Limit': 100  # Limits to 100 records per page, adjust as needed
        }

        # Use pagination token if available
        if last_evaluated_key:
            query_kwargs['ExclusiveStartKey'] = {'client_id': client_id, 'event_id': last_evaluated_key}

        # Execute paginated query
        response = event_table.query(**query_kwargs)
        
        # Fetch pagination token for the next page
        next_page_token = response.get('LastEvaluatedKey', {}).get('event_id')
        
        # Prepare response data
        data = {
            'events': response.get('Items', []),
            'next_page_token': next_page_token
        }
        
        return Response(data)
    
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







