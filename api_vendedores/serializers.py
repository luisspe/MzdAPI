import uuid
from rest_framework import serializers

class VendedorSerializer(serializers.Serializer):
    vendedor_id = serializers.CharField(max_length=40, default=uuid.uuid4)  # Usamos CharField para vendedor_id
    nombre = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    telefono = serializers.CharField(max_length=15)
    direccion = serializers.CharField(max_length=200)
    ciudad = serializers.CharField(max_length=100)
    estado = serializers.CharField(max_length=100)
    codigo_postal = serializers.CharField(max_length=10)
    sucursal = serializers.CharField(max_length=100)

class UUIDFieldToString(serializers.Field):
    def to_representation(self, value):
        return str(value)

    def to_internal_value(self, data):
        try:
            return str(uuid.UUID(data))
        except ValueError:
            raise serializers.ValidationError("Invalid UUID format.")