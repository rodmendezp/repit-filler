from __future__ import absolute_import
from celery import shared_task
from .repitfiller.repit_filler import RepitFiller


@shared_task
def get_video_candidates(n):
    repit_filler = RepitFiller()
    repit_filler.init_jobs()
    repit_filler.add_jobs(n)
