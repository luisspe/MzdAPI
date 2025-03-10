# Importaciones necesarias
from .serializers import ClientSerializer
from boto3.dynamodb.conditions import Key, Attr
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from datetime import datetime
from uuid import uuid4, UUID
from botocore.exceptions import ClientError
import uuid
import boto3
import pytz
import os

# Configuración inicial de DynamoDB
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
client_table = dynamodb.Table(os.getenv('CLIENT_TABLE_NAME', 'clients_default'))
event_table = dynamodb.Table(os.getenv('EVENT_TABLE_NAME', 'eventsv2_default'))
messages_table = dynamodb.Table(os.getenv('MESSAGE_TABLE_NAME', 'chat-mensaje-dev2'))

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
        last_evaluated_key = request.GET.get("last_evaluated_key")

        # Initial configuration for the query
        scan_kwargs = {"Limit": 100}  # Limit to 100 records per page, adjust as needed

        # Use pagination token if provided
        if last_evaluated_key:
            scan_kwargs["ExclusiveStartKey"] = {"client_id": last_evaluated_key}

        try:
            # Perform a paginated scan on the clients table
            response = client_table.scan(**scan_kwargs)

            # Obtain the pagination token for the next page
            next_page_token = response.get("LastEvaluatedKey")

            # Prepare the response data
            data = {
                "clients": response.get("Items", []),
                "next_page_token": next_page_token,
            }

            return Response(data)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
                client_id = serializer.validated_data.get("client_id")

                # Get the session_id from the request
                session_id = request.data.get("session_id")

                # If the session_id is present, update the events
                if session_id:
                    # Query to get all events with that session_id
                    response = event_table.query(
                        IndexName="session_id-index",
                        KeyConditionExpression=Key("session_id").eq(session_id),
                    )
                    events = response.get("Items", [])

                    # Update each event to add the client_id
                    for event in events:
                        event["client_id"] = client_id
                        event_table.put_item(Item=event)

                return Response(
                    {"message": "Cliente creado exitosamente.", "client_id": client_id},
                    status=status.HTTP_201_CREATED,
                )

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                return self.handle_client_error(error_code)

            except Exception as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

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
            "ProvisionedThroughputExceededException": (
                "Se ha excedido la capacidad provisionada. "
                "Por favor, inténtalo de nuevo más tarde."
            ),
            "ResourceNotFoundException": "La tabla no fue encontrada.",
            "ConditionalCheckFailedException": "La condición especificada no se cumplió.",
            "ValidationException": "Hubo un problema con los datos de entrada.",
        }
        error_message = error_messages.get(
            error_code, "Ocurrió un error al acceder a DynamoDB."
        )
        status_codes = {
            "ProvisionedThroughputExceededException": status.HTTP_503_SERVICE_UNAVAILABLE,
            "ResourceNotFoundException": status.HTTP_404_NOT_FOUND,
            "ConditionalCheckFailedException": status.HTTP_400_BAD_REQUEST, 
            "ValidationException": status.HTTP_400_BAD_REQUEST,
        }
        status_code = status_codes.get(
            error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )
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
        return Response(
            {"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND
        )

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
            return Response(
                {"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

        update_data = {**client, **request.data}
        serializer = ClientSerializer(data=update_data)
        if serializer.is_valid():
            client_table.put_item(Item=serializer.validated_data)
            return Response(
                {"message": "Cliente actualizado exitosamente."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client(self, client_id):
        """
        Helper method to retrieve a client by client_id.

        Returns:
        - The client data if found, otherwise None.
        """
        response = client_table.get_item(Key={"client_id": client_id})
        return response.get("Item", None)

    def patch(self, request, client_id):
        """
        Partially updates a specific client by client_id with the provided id_chat.

        Responses:
        - 200 OK: Client id_chat was successfully updated.
        - 400 Bad Request: Invalid data was supplied.
        - 404 Not Found: Client was not found.
        """
        client = self.get_client(client_id)
        if not client:
            return Response(
                {"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

        id_chat = request.data.get("id_chat")
        if not id_chat:
            return Response(
                {"error": "id_chat es requerido."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Actualiza solo el campo id_chat
        response = client_table.update_item(
            Key={"client_id": client_id},
            UpdateExpression="SET id_chat = :val",
            ExpressionAttributeValues={":val": id_chat},
            ReturnValues="UPDATED_NEW",
        )

        return Response(
            {"message": "id_chat actualizado exitosamente."}, status=status.HTTP_200_OK
        )

    def delete(self, request, client_id):
        # Eliminar un cliente específico por su client_id
        client_table.delete_item(Key={"client_id": client_id})
        return Response(
            {"message": "Cliente eliminado exitosamente."}, status=status.HTTP_200_OK
        )


class ClientQueryByEmailAPIView(APIView):
    """
    View for querying a client based on email.
    Supports:
    - GET: Fetches the client details based on email.
    """

    def query_client_by_email(self, email):
        """Performs a query on the database using the email."""
        return client_table.query(
            IndexName="email-index",  # Assuming you have a secondary index called 'email-index'
            KeyConditionExpression="email = :email_val",
            ExpressionAttributeValues={":email_val": email},
        )

    def get(self, request, email):
        """Handles GET requests to fetch client details using email."""
        try:
            response = self.query_client_by_email(email)
            clients = response.get("Items", [])

            if clients:
                return Response(
                    clients[0], status=status.HTTP_200_OK
                )  # Returns the first matching client
            else:
                return Response(
                    {
                        "message": "No se encontraron clientes con ese correo electrónico"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClientQueryByNumberAPIView(APIView):
    """
    View for querying a client based on number.
    Supports:
    - GET: Fetches the client details based on number.
    """

    def query_client_by_number(self, number):
        """Performs a query on the database using the number."""
        return client_table.query(
            IndexName="number-index",  # Usando el índice secundario global llamado 'number-index'
            KeyConditionExpression=Key("number").eq(number),
        )

    def get(self, request, number):
        """Handles GET requests to fetch client details using number."""
        try:
            response = self.query_client_by_number(number)
            clients = response.get("Items", [])

            if clients:
                return Response(
                    clients, status=status.HTTP_200_OK
                )  # Returns all matching clients
            else:
                return Response(
                    {"message": "No se encontraron clientes con ese número"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ClientQueryByNameAPIView(APIView):
    """
    View for querying a client based on name.
    Supports:
    - GET: Fetches the client details based on name.
    """

    def query_client_by_name(self, name):
        """Performs a query on the database using the name."""
        return client_table.query(
            IndexName="name-index",  # Usando el índice secundario global llamado 'name-index'
            KeyConditionExpression=Key("name").eq(name),
        )

    def get(self, request, name):
        """Handles GET requests to fetch client details using name."""
        try:
            response = self.query_client_by_name(name)
            clients = response.get("Items", [])

            if clients:
                filtered_clients = [
                    {
                        "client_id": client.get("client_id"),
                        "email": client.get("email"),
                        "number": client.get("number")
                    }
                    for client in clients
                ]
                return Response(
                    filtered_clients, status=status.HTTP_200_OK
                )  # Returns filtered clients with client_id, email, and number
            else:
                return Response(
                    {"message": "No se encontraron clientes con ese nombre"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# vista de eventos por client_id y session_id

class ClientEventsView(APIView):
    """
    Vista para listar todos los eventos asociados a un client_id específico.
    Se recuperan todos los eventos en batches y se devuelven en una sola respuesta.
    """

    def get(self, request, client_id):
        # Lista para almacenar todos los eventos
        all_events = []
        
        # Configuración inicial de la consulta usando el índice "client_id-index"
        query_kwargs = {
            "IndexName": "client_id-index",
            "KeyConditionExpression": Key("client_id").eq(client_id),
            # Puedes mantener o quitar el límite si lo deseas, ya que vamos a iterar hasta completar
            "Limit": 100,
        }
        
        # Bucle para ir acumulando los resultados de cada batch
        while True:
            response = event_table.query(**query_kwargs)
            all_events.extend(response.get("Items", []))
            
            # Verificar si existe más datos a través de LastEvaluatedKey
            if "LastEvaluatedKey" in response:
                query_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            else:
                break

        # Devolver todos los eventos en la respuesta
        return Response({"events": all_events})


class DeleteMessagesByPhoneNumberView(APIView):
    """
    View for deleting up to 50 messages related to a specific phone number.
    Supports:
    - DELETE: Delete up to 50 messages sent to or received from the specified phone number.
    """

    def delete(self, request, phone_number):
        """Handles DELETE requests to remove up to 50 messages by phone number."""
        try:
            # Limitar la cantidad de mensajes a eliminar en cada llamada
            limit = 50

            # Query messages sent from the phone number
            response_from = messages_table.query(
                IndexName="de_numero-index",
                KeyConditionExpression=Key("de_numero").eq(phone_number),
                Limit=limit,
                ScanIndexForward=False,
            )

            # Query messages sent to the phone number
            sended_to = messages_table.query(
                IndexName="para_numero-index",
                KeyConditionExpression=Key("para_numero").eq(phone_number),
                Limit=limit,
                ScanIndexForward=False,
            )

            # Extract messages from both responses
            messages_from = response_from.get("Items", [])
            messages_to = sended_to.get("Items", [])

            # Combine messages from both queries, ensuring we only handle up to 50 in total
            all_messages = messages_from + messages_to
            all_messages = all_messages[:limit]

            # Eliminate the messages
            for message in all_messages:
                messages_table.delete_item(
                    Key={
                        'id_chat': message['id_chat'],
                        'fecha': message['fecha'],
                    }
                )

            # Check if there might be more messages to delete
            more_messages = len(all_messages) == limit

            return Response(
                {
                    "message": "Messages deleted successfully.",
                    "more_messages": more_messages  # Indicate if there might be more messages to delete
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
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
                IndexName="de_numero-index",  # Utilizando el índice global secundario 'de_numero-index'
                KeyConditionExpression=Key("de_numero").eq(phone_number),
                ScanIndexForward=False,  # Orden inverso para obtener los mensajes más recientes primero
            )

            sended_to = messages_table.query(
                IndexName="para_numero-index",
                KeyConditionExpression=Key("para_numero").eq(phone_number),
                ScanIndexForward=False,
            )

            # Extract messages from both responses
            messages_from = response_from.get("Items", [])
            messages_to = sended_to.get("Items", [])

            # Combine messages from both queries
            all_messages = messages_from + messages_to

            return Response(all_messages, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessagesToClienteView(APIView):
    """
    View to get the most recent message sent to a specific cliente (numero_cliente).
    """
    def get(self, request, numero_cliente):
        try:
            response = messages_table.query(
                IndexName='para_numero-index',
                KeyConditionExpression=Key('para_numero').eq(numero_cliente),
                ScanIndexForward=False  # Orden inverso para obtener los mensajes más recientes primero
            )

            if response['Items']:
                mensajes = response['Items']
                # Ordenar los mensajes por fecha del más reciente al más antiguo
                mensajes.sort(key=lambda x: x['fecha'], reverse=True)
                # Devolver solo el mensaje más reciente
                ultimo_mensaje = mensajes[0]
                return Response(ultimo_mensaje, status=status.HTTP_200_OK)
            else:
                return Response({"message": "No se encontró ningún mensaje"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        



class CreditApprovalMessageView(APIView):
    """
    View to get the specific message that indicates credit approval for a cliente.
    """
    def get(self, request, numero_cliente):
        try:
            response = messages_table.query(
                IndexName='para_numero-index',
                KeyConditionExpression=Key('para_numero').eq(numero_cliente),
                FilterExpression=Attr('mensaje').contains("expediente"),
                ScanIndexForward=False  # Orden inverso para obtener los mensajes más recientes primero
            )

            if response['Items']:
                mensajes = response['Items']
                # Ordenar los mensajes por fecha del más reciente al más antiguo
                mensajes.sort(key=lambda x: x['fecha'], reverse=True)
                # Devolver solo el mensaje más reciente que cumple con el filtro
                mensaje_autorizacion = mensajes[0]
                return Response(mensaje_autorizacion, status=status.HTTP_200_OK)
            else:
                return Response({"message": "No se encontró ningún mensaje de autorización de crédito"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)