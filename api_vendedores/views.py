from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from botocore.exceptions import ClientError
from .serializers import VendedorSerializer  # Importa el serializer para el vendedor
import boto3
from boto3.dynamodb.conditions import Key
import os
# Configuración inicial de DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

client_table = dynamodb.Table(os.getenv('CLIENT_TABLE_NAME', 'clients_default'))
event_table = dynamodb.Table(os.getenv('EVENT_TABLE_NAME', 'eventsv2_default'))
vendedores_table = dynamodb.Table(os.getenv('VENDEDORES_TABLE_NAME', 'vendedores-dev'))

class VendedorByIdAPIView(APIView):
    def get(self, request, vendedor_id):
        """
        Handles GET requests to retrieve a vendedor by vendedor_id.

        Path Parameters:
        - vendedor_id: The ID of the vendedor to retrieve.

        Responses:
        - 200 OK: Returns the vendedor object if found.
        - 404 Not Found: Vendedor not found.
        - 500 Internal Server Error: Unexpected server error.
        """
        try:
            # Realizar una consulta para obtener el vendedor por su ID
            response = vendedores_table.get_item(
                Key={'vendedor_id': vendedor_id}
            )

            # Obtener el vendedor de la respuesta
            vendedor = response.get('Item')

            # Comprobar si se encontró algún vendedor
            if vendedor:
                return Response(vendedor)
            else:
                return Response({'error': 'Vendedor no encontradoo'}, status=status.HTTP_404_NOT_FOUND)

        except ClientError as e:
            return self.handle_dynamodb_error(e)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def handle_dynamodb_error(self, e):
        # Asumiendo que tienes una función que maneja errores de DynamoDB
        return VendedorCreateAPIView.handle_vendedor_error(self, e.response['Error']['Code'])
    


class ListVendedoresView(APIView):
    def get(self, request):
        """
        Handles GET requests to list all vendedores with pagination.

        Query Parameters:
        - last_evaluated_key: The last vendedor ID from the previous page; used for pagination.

        Responses:
        - 200 OK: Returns a page of vendedores along with a token for the next page.
        - 500 Internal Server Error: Unexpected server error.
        """
        # Obtener el token de paginación si se proporciona
        last_evaluated_key = request.GET.get('last_evaluated_key')

        # Configuración inicial para la consulta
        scan_kwargs = {
            'Limit': 300  # Limitar a 100 registros por página, ajustar según sea necesario
        }

        # Usar el token de paginación si se proporciona
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = {'vendedor_id': last_evaluated_key}

        try:
            # Realizar un escaneo paginado en la tabla de vendedores
            response = vendedores_table.scan(**scan_kwargs)

            # Obtener el token de paginación para la siguiente página
            next_page_token = response.get('LastEvaluatedKey')

            # Preparar los datos de respuesta
            data = {
                'vendedores': response.get('Items', []),
                'next_page_token': next_page_token
            }

            return Response(data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VendedorCreateAPIView(APIView):
    def post(self, request):
        """
        Handles POST requests to create a new vendedor.

        Request Body:
        - All fields required by the VendedorSerializer.

        Responses:
        - 201 Created: Vendedor was successfully created.
        - 400 Bad Request: Invalid data was supplied.
        - 404 Not Found: The table was not found.
        - 500 Internal Server Error: Unexpected server error.
        """
        serializer = VendedorSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Create the vendedor in the table
                vendedores_table.put_item(Item=serializer.validated_data)
                
                # Get the vendedor_id of the newly created vendedor
                vendedor_id = serializer.validated_data.get('vendedor_id')
                
                # Get the session_id from the request if needed for updating events
                session_id = request.data.get('session_id')
                
                # If the session_id is present, update the events to add the vendedor_id
                if session_id:
                    response = event_table.query(
                        IndexName='session_id-index',
                        KeyConditionExpression=Key('session_id').eq(session_id)
                    )
                    events = response.get('Items', [])

                    # Update each event to add the vendedor_id
                    for event in events:
                        event['vendedor_id'] = vendedor_id
                        event_table.put_item(Item=event)

                return Response({"message": "Vendedor creado exitosamente."}, status=status.HTTP_201_CREATED)
            
            except ClientError as e:
                error_code = e.response['Error']['Code']
                return self.handle_vendedor_error(error_code)
            
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def handle_vendedor_error(self, error_code):
        """
        Handles known client errors from DynamoDB when creating a vendedor.

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


class VendedorByEmailAPIView(APIView):
    def get(self, request, email):
        """
        Handles GET requests to retrieve a vendedor by email.

        Responses:
        - 200 OK: Returns the vendedor object if found.
        - 404 Not Found: Vendedor not found.
        - 500 Internal Server Error: Unexpected server error.
        """
        try:
            # Realizar una consulta en el índice global secundario por email
            response = vendedores_table.query(
                IndexName='email-index',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={
                    ':email': email
                }
            )

            # Obtener el vendedor de la respuesta
            vendedor = response.get('Items', [])

            # Comprobar si se encontró algún vendedor
            if vendedor:
                return Response(VendedorSerializer(vendedor[0]).data)
            else:
                return Response({'error': 'Vendedor no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        except ClientError as e:
            return self.handle_dynamodb_error(e)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)