from __future__ import absolute_import
from django.apps import apps
from celery import shared_task
from .models import GameQueueStatus, CustomQueueStatus
from .utils import get_queue_status


@shared_task
def request_jobs(game, streamer, user):
    repit_filler = apps.get_app_config('filler').repit_filler
    print('Is channel closed?', repit_filler.channel.is_closed)
    if repit_filler.channel.is_closed:
        repit_filler.reconnect()
    queue_status = get_queue_status(game, streamer, user)
    if not queue_status:
        print('Queue for game = %s, streamer = %s, user = %s was not found' % (game, streamer, user))
        return
    if queue_status.processing:
        print('Queue for game = %s, streamer = %s, user = %s already processing' % (game, streamer, user))
        return
    queue_status.locked = False
    queue_status.processing = True
    queue_status.save()
    repit_filler.add_tasks_both(game, user, streamer)
    queue_status = get_queue_status(game, streamer, user)
    queue_status.processing = False
    queue_status.save()
