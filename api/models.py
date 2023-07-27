from django.db import models

# Create your models here.
class Client(models.Model):
    client_id = models.AutoField(primary_key=True) 
    email = models.EmailField()
    name = models.CharField(max_length=100)
    number = models.CharField(max_length=15)

    def __str__(self):
        return self.name

class Event(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50)
    event_properties = models.JSONField()

    def __str__(self):
        return self.client, self.event_type
