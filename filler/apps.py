from django.apps import AppConfig


class FillerConfig(AppConfig):
    name = 'filler'

    def ready(self):
        self.reset_status()
        super().ready()

    @staticmethod
    def reset_status():
        from filler.repitfiller.repit_filler import RepitJobQueue
        from .models import Status
        status = Status.objects.get(pk=1)
        repit_job_queue = RepitJobQueue()
        status.jobs_available = repit_job_queue.jobs_available()
        status.locked = False
        status.processing = False
        status.save()
        repit_job_queue.close_connection()

