from rest_framework import status
from .base import RabbitAPI


class BindingAPI(RabbitAPI):
    def __init__(self):
        self.path = 'bindings'
        super().__init__()

    def get_bindings(self, prefix=''):
        response = self._request_get(self.path)
        if response.status_code != status.HTTP_200_OK:
            return None
        queues = []
        for queue in response.json():
            if not prefix:
                queues.append(queue)
            elif queue['name'].startswith(prefix):
                queues.append(queue)
        return queues

    def binding_exists(self, name):
        response = self._request_get(self.path)
