from __future__ import absolute_import

import os
from celery import Celery
from .settings import APPLICATION_NAME


os.environ.setdefault('DJANGO_SETTINGS_MODULE', APPLICATION_NAME + '.settings')
app = Celery(APPLICATION_NAME)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
