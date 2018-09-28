from __future__ import absolute_import
from celery import shared_task
from .models import Status
from .repitfiller.repit_filler import RepitFiller


@shared_task
def request_jobs():
    repit_filler = RepitFiller()
    repit_filler.init_jobs()
    status = Status.objects.get(pk=1)
    if status.processing:
        return
    status.locked = False
    status.processing = True
    status.save()
    repit_filler.add_jobs(100)
    status = Status.objects.get(pk=1)
    if status.locked:
        return
    status.processing = False
    status.save()
