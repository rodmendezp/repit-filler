from .api.exchange import ExchangeAPI
from .api.binding import BindingAPI
from .api.queue import QueueAPI


class RabbitMQClient(object):
    def __init__(self):
        self._exchange = None
        self._binding = None
        self._queue = None

    @property
    def exchange(self):
        if not self._exchange:
            self._exchange = ExchangeAPI()
        return self._exchange

    @property
    def binding(self):
        if not self._binding:
            self._binding = BindingAPI()
        return self._binding

    @property
    def queue(self):
        if not self._queue:
            self._queue = QueueAPI()
        return self._queue

