import uuid
from rest_framework import serializers

class ClientSerializer(serializers.Serializer):
    client_id = serializers.CharField(max_length=40)  # Si estás utilizando un ID numérico
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    number = serializers.CharField(max_length=15, required=False)
    vendedor_asignado = serializers.CharField(max_length=40, required=False)
    unidad_de_interes = serializers.CharField(max_length=50, required=False)   
    id_chat = serializers.CharField(max_length=50, required=False)
    sucursal = serializers.CharField(max_length=50, required=False)

class UUIDFieldToString(serializers.Field):
    def to_representation(self, value):
        return str(value)

    def to_internal_value(self, data):
        try:
            return str(uuid.UUID(data))
        except ValueError:
            raise serializers.ValidationError("Invalid UUID format.")