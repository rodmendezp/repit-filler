from __future__ import absolute_import
from django.apps import apps
from celery import shared_task
from .models import GameQueueStatus, CustomQueueStatus


@shared_task
def request_jobs(game, streamer, user):
    repit_filler = apps.get_app_config('filler').repit_filler
    if user:
        filler_queue_status = CustomQueueStatus.objects.filter(game=game, streamer=streamer, user=user)
    else:
        filler_queue_status = GameQueueStatus.objects.filter(game=game)
    filler_queue_status = filler_queue_status[0] if len(filler_queue_status) == 1 else None
    if filler_queue_status.processing:
        return
    filler_queue_status.locked = False
    filler_queue_status.processing = True
    filler_queue_status.save()
    if user:
        repit_filler.add_tasks_custom(game, user, streamer)
    else:
        repit_filler.add_tasks_game(game)
    if user:
        filler_queue_status = CustomQueueStatus.objects.filter(game=game, streamer=streamer, user=user)
    else:
        filler_queue_status = GameQueueStatus.objects.filter(game=game)
    filler_queue_status = filler_queue_status[0] if len(filler_queue_status) == 1 else None
    if filler_queue_status.locked:
        return
    filler_queue_status.processing = False
    filler_queue_status.save()
