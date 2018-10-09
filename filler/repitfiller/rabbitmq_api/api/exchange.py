from .base import RabbitAPI


class ExchangeAPI(RabbitAPI):
    def __init__(self):
        self.path = 'exchanges'
        super().__init__()

    def get_exchanges(self):
        response = self._request_get(self.path)

    def exchange_exists(self):
        response = self._request_get(self.path)
