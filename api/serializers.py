from rest_framework import serializers
from .models import Client, Event
class TodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["email", "name", "number"]