from .base import RabbitAPI


class BindingAPI(RabbitAPI):
    def __init__(self):
        self.path = 'bindings'
        super().__init__()

    def get_bindings(self):
        response = self._request_get(self.path)
        queues = []
        for queue in response.json():
            if not prefix:
                queues.append(queue)
            elif queue['name'].startswith(prefix):
                queues.append(queue)
        return queues

    def binding_exists(self, name):
        response = self._request_get(self.path)
