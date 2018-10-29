from django.apps import apps
from .repitfiller.repit_filler import RepitTaskQueue
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


def get_task(queue_status):
    print('Getting Task')
    repit_task_queue = RepitTaskQueue()
    message_count = repit_task_queue.get_message_count(queue_status.queue_name)
    if message_count == 1:
        queue_status.jobs_available = False
        queue_status.save()
    print('Getting repit_filler')
    repit_filler = apps.get_app_config('filler').repit_filler
    print('Repit_Filler = ', repit_filler)
    try:
        print('queue name = %s' % queue_status.queue_name)
        task = repit_filler.get_task_queue(queue_status.queue_name)
    except Exception as e:
        print('In get_task Exception')
        print(e)
    return task if task else None


def ack_task(delivery_tag):
    repit_filler = apps.get_app_config('filler').repit_filler
    response = repit_filler.ack_task(int(delivery_tag))
    return response

