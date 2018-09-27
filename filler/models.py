from django.db import models


# Create your models here.
class Status(models.Model):
    processing = models.BooleanField()
    locked = models.BooleanField()
    jobs_available = models.BooleanField()


class FillerGame(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)
    name = models.CharField(unique=True, max_length=255)
    twid = models.IntegerField(unique=True)


class FillerStreamer(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    # twid = models.IntegerField(unique=True)


class StreamerGame(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)
    streamer = models.ForeignKey(FillerStreamer, on_delete=models.DO_NOTHING)
    game = models.ForeignKey(FillerGame, on_delete=models.DO_NOTHING)
