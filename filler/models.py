from django.db import models


# Create your models here.
class Status(models.Model):
    processing = models.BooleanField()
    locked = models.BooleanField()
    jobs_available = models.BooleanField()
