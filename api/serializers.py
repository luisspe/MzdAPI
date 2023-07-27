from rest_framework import serializers
from .models import Client, Event
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["email", "name", "number"]

class EventSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    class Meta:
        model = Event
        fields = ["client", "event_type", "event_properties"]