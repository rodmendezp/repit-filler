from django.apps import apps
from .models import GameQueueStatus, CustomQueueStatus


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


def create_queue_status(game, streamer, user):
    if user:
        filler_queue_status = CustomQueueStatus.objects.create(game=game, streamer=streamer, user=user)
    else:
        filler_queue_status = GameQueueStatus.objects.create(game=game)
    return filler_queue_status


def get_or_create_queue_status(game, streamer, user):
    filler_queue_status = get_queue_status(game, streamer, user)
    if not filler_queue_status:
        filler_queue_status = create_queue_status(game, streamer, user)
    return filler_queue_status


def ack_task(delivery_tag):
    repit_filler = apps.get_app_config('filler').repit_filler
    response = repit_filler.ack_task(int(delivery_tag))
    return response

