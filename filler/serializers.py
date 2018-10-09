from rest_framework import serializers
from filler.models import *


class GameQueueStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameQueueStatus
        fields = ('id', 'game', 'processing', 'locked', 'jobs_available')


class CustomQueueStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomQueueStatus
        fields = ('id', 'game', 'streamer', 'user', 'processing', 'locked', 'jobs_available')


class FillerGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = FillerGame
        fields = ('name', )


class FillerStreamerSerializer(serializers.ModelSerializer):
    class Meta:
        model = FillerStreamer
        fields = ('name', )


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ('twid', )
