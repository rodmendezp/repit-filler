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
        if self.db_table_exists('filler_status'):
            self.reset_status()
        self.init_repit_filler()
        super().ready()

    @staticmethod
    def reset_status():
        from filler.repitfiller.repit_filler import RepitJobQueue
        from .models import Status
        try:
            status = Status.objects.get(pk=1)
        except Status.DoesNotExist:
            status = Status.objects.create(processing=False, locked=False, jobs_available=False)
        repit_job_queue = RepitJobQueue()
        status.jobs_available = repit_job_queue.jobs_available()
        status.locked = False
        status.processing = False
        status.save()
        repit_job_queue.close_connection()

    def init_repit_filler(self):
        from filler.repitfiller.repit_filler import RepitFiller
        self.repit_filler = RepitFiller()
        self.repit_filler.init_jobs()
