import requests
from rest_framework import status
from requests.compat import urljoin
from ..constants import BASE_URL


class RabbitAPI(object):
    def __init__(self, user='guest', password='guest'):
        self.user = user
        self.password = password
        super().__init__()

    @staticmethod
    def _get_request_headers():
        headers = {}
        return headers

    def _request_get(self, path, params=None, json=True, url=BASE_URL):
        url = urljoin(url, path)
        headers = self._get_request_headers()
        response = requests.get(url, params=params, headers=headers, auth=(self.user, self.password))
        if response.status_code == status.HTTP_200_OK and json:
            return response.json()
        return response
