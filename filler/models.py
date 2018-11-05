from django.db import models
from .repitfiller.utils import params_to_queue_name


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


class Video(models.Model):
    id = models.AutoField(db_column='ID', primary_key=True)
    twid = models.IntegerField(unique=True)


class GameQueueStatus(models.Model):
    game = models.CharField(max_length=255, unique=True)
    processing = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    jobs_available = models.BooleanField(default=False)
    message = models.CharField(max_length=255, default='')

    @property
    def queue_name(self):
        return params_to_queue_name(self.game)


class CustomQueueStatus(models.Model):
    game = models.CharField(max_length=255)
    streamer = models.CharField(max_length=255)
    user = models.CharField(max_length=255)
    processing = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    jobs_available = models.BooleanField(default=False)
    message = models.CharField(max_length=255, default='')

    @property
    def queue_name(self):
        return params_to_queue_name(self.game, self.streamer, self.user)
