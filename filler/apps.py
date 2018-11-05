from django.apps import AppConfig
from django.db import connection


class FillerConfig(AppConfig):
    name = 'filler'

    def __init__(self, app_name, app_module):
        self.repit_filler = None
        super().__init__(app_name, app_module)

    @staticmethod
    def db_table_exists(table_name):
        return table_name in connection.introspection.table_names()

    def ready(self):
        self.init_repit_filler()
        self.repit_filler.clear_all_custom_queue()
        if self.db_table_exists('filler_gamequeuestatus'):
            self.reset_status()
        super().ready()

    @staticmethod
    def reset_status():
        from filler.repitfiller.repit_filler import RepitTaskQueue
        from filler.repitfiller.utils import params_to_queue_name
        from .models import GameQueueStatus, CustomQueueStatus
        game_queues = GameQueueStatus.objects.all()
        repit_task_queue = RepitTaskQueue()
        custom_queues = CustomQueueStatus.objects.all()
        custom_queues.delete()
        print()
        for game_queue in game_queues:
            queue = params_to_queue_name(game_queue.game)
            print('Messages in queue %s: %s' % (queue, repit_task_queue.get_message_count(queue)))
            game_queue.jobs_available = repit_task_queue.tasks_available(queue)
            game_queue.processing = False
            game_queue.locked = False
            game_queue.message = ''
            game_queue.save()
        print()

    def init_repit_filler(self):
        from filler.repitfiller.repit_filler import RepitFiller
        self.repit_filler = RepitFiller()
        self.repit_filler.connect()
        self.repit_filler.get_game_queues()
