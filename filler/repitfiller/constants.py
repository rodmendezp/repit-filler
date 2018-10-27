import os

EXCHANGE_NAME = 'repit_tasks'
RABBIT_HOST = 'localhost'
TASKS_GAME = 100
TASKS_CUSTOM = 20
REPITIT_FILLER_HOST = 'http://%s' % os.environ.get('SERVER_INTERNAL_IP', '127.0.0.1:9999')
FILLER_API = '%s/filler' % REPITIT_FILLER_HOST
GAME_QUEUE_ENDPOINT = '%s/game_queue_status/' % FILLER_API
CUSTOM_QUEUE_ENDPOINT = '%s/custom_queue_status/' % FILLER_API
