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
event_table = dynamodb.Table('events')

# Vista para listar todos los clientes
class ListClientsView(APIView):
    def get(self, request):
        # Obtener el token de paginación si se proporciona
        last_evaluated_key = request.GET.get('last_evaluated_key')

        # Configuración inicial para la consulta
        scan_kwargs = {
            'Limit': 100  # Limita a 10 registros por página, puedes ajustar esto según tus necesidades
        }

        # Si hay un token de paginación, úsalo
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = {'client_id': last_evaluated_key}

        # Realizar un escaneo de la tabla de clientes con paginación
        response = client_table.scan(**scan_kwargs)

        # Obtener el token de paginación para la próxima página
        next_page_token = response.get('LastEvaluatedKey')

        # Preparar la respuesta
        data = {
            'clients': response.get('Items', []),
            'next_page_token': next_page_token
        }

        return Response(data)

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
            
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ProvisionedThroughputExceededException':
                    return Response({"error": "Se ha excedido la capacidad provisionada. Por favor, inténtalo de nuevo más tarde."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                elif error_code == 'ResourceNotFoundException':
                    return Response({"error": "La tabla no fue encontrada."}, status=status.HTTP_404_NOT_FOUND)
                elif error_code == 'ConditionalCheckFailedException':
                    return Response({"error": "La condición especificada no se cumplió."}, status=status.HTTP_400_BAD_REQUEST)
                elif error_code == 'ValidationException':
                    return Response({"error": "Hubo un problema con los datos de entrada."}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": "Ocurrió un error al acceder a DynamoDB."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    

class ClientQueryByEmailAPIView(APIView):
    def get(self, request, email):
        try:
            # Realizar la consulta utilizando el índice secundario del correo electrónico
            response = client_table.query(
                IndexName='email-index',  # Asumiendo que tienes un índice secundario llamado 'email-index'
                KeyConditionExpression='email = :email_val',
                ExpressionAttributeValues={
                    ':email_val': email
                }
            )
            
            clients = response.get('Items', [])
            
            if len(clients) > 0:
                return Response(clients[0], status=status.HTTP_200_OK)  # Devuelve el primer cliente que coincida
            else:
                return Response({"message": "No se encontraron clientes con ese correo electrónico"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        try:
            if 'event_source' in request.data and request.data['event_source'] != 'physical_location':
                if 'session_id' not in request.data:
                    request.data['session_id'] = str(uuid4())
            if 'event_id' not in request.data:
                request.data['event_id'] = str(uuid4())
            serializer = EventSerializer(data=request.data)
            if serializer.is_valid():
                event_data = serializer.validated_data
                mexico_tz = pytz.timezone('America/Mexico_City')
                mexico_time = datetime.now(mexico_tz)
                event_data['timestamp'] = mexico_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')
                if isinstance(event_data.get('event_id'), uuid.UUID):
                    event_data['event_id'] = str(event_data['event_id'])


                # Convertir session_id a string solo si está presente y es una instancia de uuid.UUID
                if event_data.get('session_id') and isinstance(event_data.get('session_id'), uuid.UUID):
                    event_data['session_id'] = str(event_data['session_id'])


                event_table.put_item(Item=event_data)
                return Response({"message": "Evento creado exitosamente."}, status=status.HTTP_201_CREATED)
        
        except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ProvisionedThroughputExceededException':
                    return Response({"error": "Se ha excedido la capacidad provisionada. Por favor, inténtalo de nuevo más tarde."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                elif error_code == 'ResourceNotFoundException':
                    return Response({"error": "La tabla no fue encontrada."}, status=status.HTTP_404_NOT_FOUND)
                elif error_code == 'ConditionalCheckFailedException':
                    return Response({"error": "La condición especificada no se cumplió."}, status=status.HTTP_400_BAD_REQUEST)
                elif error_code == 'ValidationException':
                    return Response({"error": "Hubo un problema con los datos de entrada."}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": "Ocurrió un error al acceder a DynamoDB."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
        # Obtener el token de paginación si se proporciona
        last_evaluated_key = request.GET.get('last_evaluated_key')
        
        # Configuración inicial para la consulta
        query_kwargs = {
            'IndexName': 'client_id-index',
            'KeyConditionExpression': Key('client_id').eq(client_id),
            'Limit': 100  # Limita a 10 registros por página
        }

        # Si hay un token de paginación, úsalo
        if last_evaluated_key:
            query_kwargs['ExclusiveStartKey'] = {'client_id': client_id, 'event_id': last_evaluated_key}

        # Realizar la consulta con paginación
        response = event_table.query(**query_kwargs)
        
        # Obtener el token de paginación para la próxima página
        next_page_token = response.get('LastEvaluatedKey', {}).get('event_id')
        
        # Preparar la respuesta
        data = {
            'events': response.get('Items', []),
            'next_page_token': next_page_token
        }
        
        return Response(data)
    
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

class TodaysVisitsApiView(APIView):
    def get(self, request):
         # Establecer la zona horaria para la Ciudad de México
        mexico_tz = pytz.timezone('America/Mexico_City')
        # Obtener la fecha actual en esa zona horaria
        today = datetime.now(mexico_tz).strftime('%Y-%m-%d')
        

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







