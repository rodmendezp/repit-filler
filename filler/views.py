from django.apps import apps
from rest_framework import status, generics
from django.forms.models import model_to_dict
from rest_framework.views import APIView, Response

from .tasks import request_jobs
from .utils import get_queue_status, ack_task
from .utils import get_or_create_queue_status, get_request_params
from .serializers import FillerGameSerializer, FillerStreamerSerializer
from .serializers import GameQueueStatusSerializer, CustomQueueStatusSerializer
from .models import FillerGame, FillerStreamer, StreamerGame, GameQueueStatus, CustomQueueStatus


class TaskView(APIView):
    def get(self, request):
        game, streamer, user = get_request_params(request.query_params)
        print('Getting task game = %s, streamer = %s, user = %s' % (game, streamer, user))
        queue_status = get_or_create_queue_status(game, streamer, user)
        print('Queue Status = ', queue_status)
        repit_filler = apps.get_app_config('filler').repit_filler
        print('Is channel closed?', repit_filler.channel.is_closed)
        if repit_filler.channel.is_closed:
            repit_filler.reconnect()
        if not queue_status or not queue_status.jobs_available:
            data = {'task': None}
        elif queue_status.jobs_available:
            data = {'task': repit_filler.get_task(queue_status)}
        elif queue_status.message:
            data = {'exception': queue_status.message}
            queue_status.message = ''
            queue_status.save()
        print('TaskView GET ending')
        print(data)
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        delivery_tag = request.data.get('delivery_tag', None)
        if not delivery_tag:
            return Response({'error': 'Bad Request'}, status=status.HTTP_400_BAD_REQUEST)
        response = ack_task(delivery_tag)
        return Response(response, status=status.HTTP_200_OK)


class StatusView(APIView):
    def get(self, request):
        game, streamer, user = get_request_params(request.query_params)
        queue_status = get_queue_status(game, streamer, user)
        if not queue_status:
            return Response({'error': 'Queue Does Not Exist'}, status=status.HTTP_400_BAD_REQUEST)
        data = {'queue_status': model_to_dict(queue_status)}
        return Response(data, status=status.HTTP_200_OK)


class ProcessView(APIView):
    def get(self, request):
        game, streamer, user = get_request_params(request.query_params)
        queue_status = get_queue_status(game, streamer, user)
        if not queue_status:
            return Response({'error': 'Queue Does Not Exist'}, status=status.HTTP_400_BAD_REQUEST)
        locked = queue_status.locked
        processing = queue_status.processing
        message = ''
        if not locked and not processing:
            message = 'Processing Started'
            queue_status.locked = True
            queue_status.save()
            request_jobs.delay(game, streamer, user)
        elif locked and processing:
            message = 'Something went wrong'
        elif locked and not processing:
            message = 'There is a previous request'
        elif not locked and processing:
            message = 'Already processing'
        data = {'queue_status': model_to_dict(queue_status), 'message': message}
        return Response(data, status=status.HTTP_200_OK)


class GameQueueStatusList(generics.ListCreateAPIView):
    queryset = GameQueueStatus.objects.all()
    serializer_class = GameQueueStatusSerializer

    def get_queryset(self):
        queryset = GameQueueStatus.objects.all()
        game = self.request.query_params.get('game', None)
        queryset = queryset.filter(game=game) if game else queryset
        return queryset


class GameQueueStatusDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = GameQueueStatus.objects.all()
    serializer_class = GameQueueStatusSerializer


class CustomQueueStatusList(generics.ListCreateAPIView):
    queryset = CustomQueueStatus.objects.all()
    serializer_class = CustomQueueStatusSerializer

    def get_queryset(self):
        queryset = CustomQueueStatus.objects.all()
        game = self.request.query_params.get('game', None)
        streamer = self.request.query_params.get('streamer', None)
        user = self.request.query_params.get('user', None)
        queryset = queryset.filter(game=game) if game else queryset
        queryset = queryset.filter(streamer=streamer) if streamer else queryset
        queryset = queryset.filter(user=user) if user else queryset
        return queryset


class CustomQueueStatusDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomQueueStatus.objects.all()
    serializer_class = CustomQueueStatusSerializer


class FillerGameList(generics.ListCreateAPIView):
    queryset = FillerGame.objects.all()
    serializer_class = FillerGameSerializer


class FillerStreamerList(generics.ListCreateAPIView):
    queryset = FillerStreamer.objects.all()
    serializer_class = FillerStreamerSerializer

    def get(self, request, *args, **kwargs):
        game = request.query_params.get('game', None)
        game_defaults = request.query_params.get('game_defaults', None)
        if game:
            repit_filler = apps.get_app_config('filler').repit_filler
            streamers = repit_filler.get_game_streamers(game)
            data = {'streamers': streamers}
            return Response(data, status.HTTP_200_OK)
        elif game_defaults:
            try:
                streamers = StreamerGame.objects.filter(game__name=game_defaults)
                streamers = list(map(lambda x: x.streamer.name, streamers))
                data = {'streamers': streamers}
                return Response(data, status.HTTP_200_OK)
            except FillerGame.DoesNotExist:
                pass
        return super().get(request, *args, **kwargs)
