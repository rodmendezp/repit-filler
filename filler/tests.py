import requests
from django.test import TestCase
from filler.repitfiller.repit_filler import RepitFiller
from filler.repitfiller.rabbitmq_api.client import RabbitMQClient


class RepitFillerTest(TestCase):
    def setUp(self):
        super().setUp()

    def test_repit_filler_creation(self):
        repit_filler = RepitFiller()
        repit_filler.init_jobs()
        self.assertEqual(repit_filler.connection.is_open, True)
        self.assertEqual(repit_filler.jobs_queue.channel_number, repit_filler.jobs_channel_id)
        self.assertEqual(repit_filler.jobs_queue.method.queue, repit_filler.jobs_queue_name)


class RepitFillerFillTest(TestCase):
    def setUp(self):
        self.repit_filler = RepitFiller()
        self.repit_filler.init_jobs()
        self.repit_filler.init_request()
        super().setUp()

    def test_add_jobs(self):
        self.repit_filler.add_jobs(5)


class RepitAPITest(TestCase):
    def setUp(self):
        self.baseURL = 'http://127.0.0.1:8000/'
        self.twitchDataURL = self.baseURL + 'twitchdata/'
        super().setUp()

    def test_get_twitch_users(self):
        twitch_user_url = self.twitchDataURL + 'twitch_user/'
        response = requests.get(twitch_user_url)
        print(response)


class RabbitMQAPITest(TestCase):
    def setUp(self):
        super().setUp()

    def test_get_queues(self):
        self.rabbitmq_client = RabbitMQClient()
        queues = self.rabbitmq_client.queue.get_queues()
        queues_names = list(map(lambda x: x['name'], queues))
        bindings = []
        for queue_name in queues_names:
            bindings.append(self.rabbitmq_client.queue.get_queue_bindings(queue_name))
        print(bindings)
        pass
