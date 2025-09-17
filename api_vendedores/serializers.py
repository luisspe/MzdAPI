import uuid
from rest_framework import serializers

class VendedorSerializer(serializers.Serializer):
    vendedor_id = serializers.CharField(max_length=40)  # Usamos CharField para vendedor_id
    nombre = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    telefono = serializers.CharField(max_length=15)
    direccion = serializers.CharField(max_length=200)
    ciudad = serializers.CharField(max_length=100)
    estado = serializers.CharField(max_length=100)
    codigo_postal = serializers.CharField(max_length=10)
    sucursal = serializers.CharField(max_length=100)
    activo = serializers.BooleanField(default=True)

    def create(self, validated_data):
        # Convierte el UUID a una cadena antes de crear el objeto
        validated_data['vendedor_id'] = str(uuid.uuid4())
        return super().create(validated_data)