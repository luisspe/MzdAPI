import uuid
from rest_framework import serializers

class ClientSerializer(serializers.Serializer):
    client_id = serializers.CharField(max_length=40, allow_blank=True)  # Asumiendo que es un CharField
    name = serializers.CharField(max_length=200, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    vendedor_asignado = serializers.CharField(max_length=40, required=False, allow_blank=True)
    unidad_de_interes = serializers.CharField(max_length=50, required=False, allow_blank=True)
    id_chat = serializers.CharField(max_length=50, required=False, allow_blank=True)
    sucursal = serializers.CharField(max_length=50, required=False, allow_blank=True)
    personal_chat = serializers.CharField(max_length=40, required=False, allow_blank=True)
    id_chat_instagram = serializers.CharField(max_length=80, required=False, allow_blank=True)
    instagram_username = serializers.CharField(max_length=40, required=False, allow_blank=True)
    instagram_user_id = serializers.CharField(max_length=40, required=False, allow_blank=True)
    
class UUIDFieldToString(serializers.Field):
    def to_representation(self, value):
        return str(value)

    def to_internal_value(self, data):
        try:
            return str(uuid.UUID(data))
        except ValueError:
            raise serializers.ValidationError("Invalid UUID format.")