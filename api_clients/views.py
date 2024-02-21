# Importaciones necesarias
from .serializers import ClientSerializer
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


# Configuración inicial de DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
client_table = dynamodb.Table('clients')
event_table = dynamodb.Table('eventsv2')
messages_table = dynamodb.Table('chat_mensaje')

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

class MessagesByPhoneNumberView(APIView):
    """
    View for retrieving messages related to a specific phone number.
    Supports:
    - GET: Retrieve messages sent to or received from the specified phone number.
    """

    def get(self, request, phone_number):
        """Handles GET requests to retrieve messages by phone number."""
        try:
            # Perform two separate queries on the chat messages table
            response_from = messages_table.query(
                IndexName='de_numero-index',  # Utilizando el índice global secundario 'de_numero-index'
                KeyConditionExpression=Key('de_numero').eq(phone_number),
                ScanIndexForward=False  # Orden inverso para obtener los mensajes más recientes primero
            )

            sended_to = messages_table.query(
                IndexName='para_numero-index',
                KeyConditionExpression=Key('para_numero').eq(phone_number),
                ScanIndexForward=False
            )

            
            # Extract messages from both responses
            messages_from = response_from.get('Items', [])
            messages_to = sended_to.get('Items', [])

            # Combine messages from both queries
            all_messages = messages_from + messages_to

            return Response(all_messages, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)