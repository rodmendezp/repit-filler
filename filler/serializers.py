from rest_framework import serializers
from filler.models import FillerGame, FillerStreamer


class FillerGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = FillerGame
        fields = ('name', )


class FillerStreamerSerializer(serializers.ModelSerializer):
    class Meta:
        model = FillerStreamer
        fields = ('name', )
