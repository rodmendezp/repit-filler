from .base import RabbitAPI
from urllib.parse import quote
from rest_framework import status


class QueueAPI(RabbitAPI):
    def __init__(self):
        self.path = 'queues'
        super().__init__()

    def get_queues(self, prefix=''):
        response = self._request_get(self.path)
        if response.status_code != status.HTTP_200_OK:
            return None
        response = response.json()
        queues = []
        for queue in response:
            if not prefix:
                queues.append(queue)
            elif queue['name'].startswith(prefix):
                queues.append(queue)
        return queues

    def get_queue_bindings(self, name, exchange='', vhost='/'):
        vhost = quote(vhost, '')
        path = '%s/%s/%s/bindings' % (self.path, vhost, name)
        response = self._request_get(path)
        if response.status_code != status.HTTP_200_OK:
            return None
        response = response.json()
        if exchange:
            binding = list(filter(lambda x: x['source'] == exchange, response))
        else:
            binding = list(filter(lambda x: x['destination'] != x['routing_key'], response))
        return binding[0]['routing_key'] if len(binding) == 1 else None

    def get_queue_message_count(self, name, vhost='/'):
        vhost = quote(vhost, '')
        path = '%s/%s/%s' % (self.path, vhost, name)
        response = self._request_get(path)
        if response.status_code != status.HTTP_200_OK:
            return None
        response = response.json()
        return response.get('messages', None)

    def tasks_available(self, name, vhost='/'):
        tasks = self.get_queue_message_count(name, vhost)
        if not isinstance(tasks, int):
            return False
        return tasks > 0

