from django.apps import apps
from django.http import JsonResponse
from django.conf import settings
from django.forms.models import model_to_dict
from rest_framework import status, generics
from rest_framework.views import APIView, Response

from .serializers import *
from .models import GameQueueStatus, CustomQueueStatus
from .tasks import request_jobs
from .repitfiller.repit_filler import RepitTaskQueue
from .repitfiller.utils import params_to_queue_name


def ack_job(delivery_tag):
    repit_filler = apps.get_app_config('filler').repit_filler
    response = repit_filler.ack_task(int(delivery_tag))
    return response


def get_job(game, streamer='', user=''):
    repit_task_queue = RepitTaskQueue()
    queue = params_to_queue_name(game, streamer, user)
    message_count = repit_task_queue.get_message_count(queue)
    if message_count == 1:
        filler_queue_status = get_queue_status(game, streamer, user)
        filler_queue_status.jobs_available = False
        filler_queue_status.save()
    repit_filler = apps.get_app_config('filler').repit_filler
    return repit_filler.get_job(game, streamer, user)


def get_request_params(params):
    game = params.get('game', None)
    streamer = params.get('streamer', '')
    user = params.get('user', '')
    return game, streamer, user


def get_queue_status(game, streamer, user):
    if user:
        filler_queue_status = CustomQueueStatus.objects.filter(game=game, streamer=streamer, user=user)
    else:
        filler_queue_status = GameQueueStatus.objects.filter(game=game)
    return filler_queue_status[0] if len(filler_queue_status) == 1 else None


def get_or_create_queue_status(game, streamer, user):
    filler_queue_status = get_queue_status(game, streamer, user)
    if not filler_queue_status and user:
        filler_queue_status = CustomQueueStatus.objects.create(game=game, streamer=streamer, user=user)
    elif not filler_queue_status and not user:
        filler_queue_status = GameQueueStatus.objects.create(game=game)
    return filler_queue_status


class JobsAvailableView(APIView):
    def get(self, request, format=None):
        game, streamer, user = get_request_params(request.query_params)
        filler_queue_status = get_or_create_queue_status(game, streamer, user)
        data = {'jobs_available': 'yes' if filler_queue_status.jobs_available else 'no'}
        if filler_queue_status.jobs_available:
            data['job'] = get_job(game, streamer, user)
        return JsonResponse(data)

    def put(self, request, format=None):
        game, streamer, user = get_request_params(request.query_params)
        filler_queue_status = get_queue_status(game, streamer, user)
        jobs_available = request.data.get('jobs_available', None)
        if jobs_available and (jobs_available == 'True' or jobs_available == 'False'):
            filler_queue_status.jobs_available = jobs_available == 'True'
            filler_queue_status.save()
            return Response({'filler_status': model_to_dict(filler_queue_status)})
        return Response({'error': 'request data need to be boolean'}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, format=None):
        delivery_tag = request.data.get('delivery_tag', None)
        if not delivery_tag:
            return Response({'error': 'no delivery_tag'}, status=status.HTTP_400_BAD_REQUEST)
        response = ack_job(delivery_tag)
        return Response(response, status=status.HTTP_200_OK)

    def options(self, request, *args, **kwargs):
        print(request)
        return super().options(request, *args, **kwargs)


class StatusView(APIView):
    def get(self, request, format=None):
        game, streamer, user = get_request_params(request.query_params)
        filler_queue_status = get_queue_status(game, streamer, user)
        data = {
            'status_short': 'processing' if filler_queue_status.processing else 'idle',
            'filler_status': model_to_dict(filler_queue_status)
        }
        return JsonResponse(data)


class RequestJobs(APIView):
    def get(self, request, format=None):
        game, streamer, user = get_request_params(request.query_params)
        filler_queue_status = get_queue_status(game, streamer, user)
        processing = filler_queue_status.processing
        locked = filler_queue_status.locked
        request_response = ''
        if locked and processing:
            request_response = 'Something went wrong'
        elif locked and not processing:
            request_response = 'There is a previous request'
        elif not locked and processing:
            request_response = 'Already processing'
        elif not locked and not processing:
            request_response = 'Processing started'
            try:
                filler_queue_status.locked = True
                filler_queue_status.save()
                if settings.NO_CELERY:
                    request_jobs(game, streamer, user)
                else:
                    request_jobs.delay(game, streamer, user)
            except Exception as e:
                request_response = 'There was an error when starting the processing %s' % repr(e)
        data = {'filler_status': model_to_dict(filler_queue_status), 'request_response': request_response}
        return JsonResponse(data)


class CancelJobs(APIView):
    def get(self, request, format=None):
        game, streamer, user = get_request_params(request.query_params)
        filler_queue_status = get_queue_status(game, streamer, user)
        locked = filler_queue_status.locked
        processing = filler_queue_status.processing
        cancel_response = ''
        if locked and processing:
            cancel_response = 'Something went wrong'
        elif locked and not processing:
            cancel_response = 'There is a previous request'
        elif not locked and processing:
            try:
                filler_queue_status.locked = True
                filler_queue_status.save()
                filler_queue_status.processing = False
                filler_queue_status.locked = False
                filler_queue_status.save()
                cancel_response = 'Processing Cancelled'
            except Exception as e:
                cancel_response = 'There was an error when cancelling the processing %s' % repr(e)
        elif not locked and not processing:
            cancel_response = ''
        data = {'filler_status': model_to_dict(filler_queue_status), 'cancel_response': cancel_response}
        return JsonResponse(data)


class ClearJobs(APIView):
    def get(self, request, format=None):
        game, streamer, user = get_request_params(request.query_params)
        filler_queue_status = get_queue_status(game, streamer, user)
        filler_queue_status.jobs_available = True
        filler_queue_status.save()
        return JsonResponse({'filler_status': model_to_dict(filler_queue_status)})


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
            return JsonResponse({'streamers': streamers})
        elif game_defaults:
            try:
                streamers = StreamerGame.objects.filter(game__name=game_defaults)
                streamers = list(map(lambda x: x.streamer.name, streamers))
                return JsonResponse({'streamers': streamers})
            except FillerGame.DoesNotExist:
                pass
        return super().get(request, *args, **kwargs)


class VideoList(generics.ListCreateAPIView):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer


class VideoDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
