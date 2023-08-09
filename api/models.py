from django.db import models

# Create your models here.
class Client(models.Model):
    client_id = models.CharField(max_length=40) 
    email = models.EmailField(null=True)
    name = models.CharField(max_length=100, null=True)
    number = models.CharField(max_length=15, null=True)
    session_id = models.CharField(max_length=200, null=True)

    def __str__(self):
        return self.name

class Event(models.Model):
    client_id = models.CharField(max_length=50)
    event_type = models.CharField(max_length=50)
    event_properties = models.JSONField()

    def __str__(self):
        return self.client, self.event_type
