import uuid
from rest_framework import serializers

class ClientSerializer(serializers.Serializer):
    client_id = serializers.CharField(max_length=40)  # Si estás utilizando un ID numérico
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    number = serializers.CharField(max_length=15)
    vendedor_asignado = serializers.CharField(max_length=40)
    unidad_de_interes = serializers.CharField(max_length=50)
    

class UUIDFieldToString(serializers.Field):
    def to_representation(self, value):
        return str(value)

    def to_internal_value(self, data):
        try:
            return uuid.UUID(data)
        except ValueError:
            raise serializers.ValidationError("Invalid UUID format.")

class EventSerializer(serializers.Serializer):
    event_id = UUIDFieldToString(required=False)
    session_id = UUIDFieldToString(required=False)
    client_id = serializers.CharField(max_length=40, required=False)
    event_type = serializers.CharField(max_length=50) 
    event_data = serializers.JSONField()
    timestamp = serializers.DateTimeField(required=False)


