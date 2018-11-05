from __future__ import absolute_import
from django.apps import apps
from celery import shared_task
from .utils import get_queue_status
from .repitfiller.twitch_video import NoVideosException, NoStreamerException
from celery.exceptions import SoftTimeLimitExceeded


@shared_task(soft_time_limit=300, time_limit=315)
def request_jobs(game, streamer, user):
    repit_filler = apps.get_app_config('filler').repit_filler
    try:
        repit_filler.connect()
        repit_filler.get_game_queues()
        queue_status = get_queue_status(game, streamer, user)
        if not queue_status or queue_status.processing:
            return
        queue_status.locked = False
        queue_status.processing = True
        queue_status.save()
        try:
            repit_filler.add_tasks_both(game, streamer, user)
        except NoVideosException:
            queue_status.message = 'Seems that all videos have been labeled or are restricted'
            print(queue_status.message)
            queue_status.save()
        except NoStreamerException:
            queue_status.message = 'Did not found any top streamers with their channels in English'
            print(queue_status.message)
            queue_status.save()
        queue_status = get_queue_status(game, streamer, user)
        queue_status.processing = False
        queue_status.save()
        repit_filler.close_connection()
    except SoftTimeLimitExceeded:
        print('SoftTimeLimitExceeded Exception')
        queue_status = get_queue_status(game, streamer, user)
        queue_status.processing = False
        queue_status.save()

