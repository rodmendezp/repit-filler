from .base import RabbitAPI
from urllib.parse import quote


class QueueAPI(RabbitAPI):
    def __init__(self):
        self.path = 'queues'
        super().__init__()

    def get_queues(self, prefix=''):
        response = self._request_get(self.path)
        queues = []
        for queue in response:
            if not prefix:
                queues.append(queue)
            elif queue['name'].startswith(prefix):
                queues.append(queue)
        return queues

    def queue_exists(self):
        response = self._request_get(self.path)
        pass

    def get_queue_bindings(self, name, exchange='', vhost='/'):
        vhost = quote(vhost, '')
        path = '%s/%s/%s/bindings' % (self.path, vhost, name)
        response = self._request_get(path)
        if exchange:
            binding = list(filter(lambda x: x['source'] == exchange, response))
        else:
            binding = list(filter(lambda x: x['destination'] != x['routing_key'], response))
        return binding[0]['routing_key'] if len(binding) == 1 else None
