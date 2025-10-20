import uuid
from rest_framework import serializers

class VendedorSerializer(serializers.Serializer):
    vendedor_id = serializers.CharField(max_length=40)
    nombre = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    telefono = serializers.CharField(max_length=15, allow_blank=True) # Permitir teléfono vacío
    direccion = serializers.CharField(max_length=200, allow_blank=True) # Permitir campos vacíos
    ciudad = serializers.CharField(max_length=100, allow_blank=True)
    estado = serializers.CharField(max_length=100, allow_blank=True)
    codigo_postal = serializers.CharField(max_length=10, allow_blank=True)
    sucursal = serializers.CharField(max_length=100)
    activo = serializers.BooleanField(default=True)
    
    # --- CAMBIO AQUÍ ---
    # Añadimos el campo gsi_pk. No es requerido en la entrada de la API.
    gsi_pk = serializers.CharField(required=False)

    def validate(self, data):
        """
        Este método se llama durante la validación.
        Lo usamos para añadir automáticamente el campo gsi_pk a los datos validados.
        """
        # --- CAMBIO AQUÍ ---
        # Añade el valor estático para el GSI a todos los nuevos vendedores
        data['gsi_pk'] = 'VENDEDORES'

        # NOTA: Tu vista `VendedorCreateAPIView` no genera un `vendedor_id`.
        # Si un nuevo vendedor no lo incluye en el request, fallará.
        # Podrías añadir la generación del UUID aquí si lo necesitas:
        if 'vendedor_id' not in data or not data['vendedor_id']:
             data['vendedor_id'] = str(uuid.uuid4())
        
        return data

    # El método 'create' no es usado por tu VendedorCreateAPIView, 
    # pero lo dejamos por si se usa en otro lado.
    def create(self, validated_data):
        return validated_data