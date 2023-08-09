import boto3
from moto import mock_dynamodb
from rest_framework.test import APITestCase
from api.serializers import ClientSerializer, EventSerializer
import uuid

boto3.setup_default_session(aws_access_key_id='testing', aws_secret_access_key='testing', region_name='us-west-2')

class ClientTests(APITestCase):

    @mock_dynamodb
    def setUp(self):
        # Crear una tabla mock de DynamoDB para Clientes
        self.dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
        self.client_table = self.dynamodb.create_table(
            TableName='Client',
            KeySchema=[
                {
                    'AttributeName': 'client_id',
                    'KeyType': 'HASH'
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'client_id',
                    'AttributeType': 'S'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )

        # Crear una tabla mock de DynamoDB para Eventos
        self.event_table = self.dynamodb.create_table(
            TableName='Event',
            KeySchema=[
                {
                    'AttributeName': 'event_id',
                    'KeyType': 'HASH'
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'event_id',
                    'AttributeType': 'S'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )

    @mock_dynamodb
    def test_create_client(self):
        client_data = {
            'client_id': '12345',
            'name': 'John Doe',
            'email': 'john@example.com',
            'number': '1234567890'
        }
        serializer = ClientSerializer(data=client_data)
        self.assertTrue(serializer.is_valid())
        self.client_table.put_item(Item=client_data)

        # Ahora puedes hacer una solicitud a tu API y verificar si maneja correctamente el cliente que acabas de agregar.
        response = self.client.get('/api/clients/')  # Asume que este es el endpoint para obtener clientes
        self.assertEqual(response.status_code, 200)
        self.assertIn(client_data, response.data)

    @mock_dynamodb
    def test_create_event(self):
        event_data = {
            'event_id': str(uuid.uuid4()),
            'session_id': str(uuid.uuid4()),
            'client_id': '12345',
            'event_type': 'login',
            'event_data': {'key': 'value'},
            'timestamp': '2023-08-07T12:34:56Z'  # Asume que este es el formato de fecha/hora que estás usando
        }
        serializer = EventSerializer(data=event_data)
        self.assertTrue(serializer.is_valid())
        self.event_table.put_item(Item=event_data)

        # Ahora puedes hacer una solicitud a tu API y verificar si maneja correctamente el evento que acabas de agregar.
        response = self.client.get('/api/events/')  # Asume que este es el endpoint para obtener eventos
        self.assertEqual(response.status_code, 200)
        self.assertIn(event_data, response.data)
