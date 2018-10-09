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
        if self.db_table_exists('filler_gamequeuestatus'):
            self.reset_status()
        self.init_repit_filler()
        super().ready()

    @staticmethod
    def reset_status():
        from filler.repitfiller.repit_filler import RepitJobQueue
        from .models import GameQueueStatus, CustomQueueStatus
        game_queues = GameQueueStatus.objects.all()
        for game_queue in game_queues:
            repit_job_queue = RepitJobQueue(game_queue.game)
            game_queue.jobs_available = repit_job_queue.jobs_available()
            game_queue.processing = False
            game_queue.locked = False
            game_queue.save()
            repit_job_queue.close_connection()
        custom_queues = CustomQueueStatus.objects.all()
        custom_queues.delete()

    def init_repit_filler(self):
        from filler.repitfiller.repit_filler import RepitFiller
        self.repit_filler = RepitFiller()
        self.repit_filler.init()
