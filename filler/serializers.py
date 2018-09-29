from rest_framework import serializers
from filler.models import *


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
        fields = ('twid', 'candidates')


class CandidateSerializer(serializers.ModelSerializer):
    video = VideoSerializer

    class Meta:
        model = Candidate
        fields = ('video', 'start', 'end', 'ack')
