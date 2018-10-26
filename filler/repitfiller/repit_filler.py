import pika
import pickle
import requests
from rest_framework import status
from django.conf import settings

from . import constants
from .twitch_chat import TwitchChat
from .twitch_video import TwitchVideo
from .twitch_highlight import TwitchHighlight
from .rabbitmq_api.client import RabbitMQClient
from .utils import params_to_queue_name, params_to_routing_key, routing_key_to_params


class RepitFiller:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queues = []
        self.queues_id = {}
        self.routing_keys = []
        self.game = None
        self.streamer = None
        self.user = None
        self.rabbitmq_client = RabbitMQClient()
        self.twitch_video = TwitchVideo()

    def init(self):
        params = pika.ConnectionParameters(host=constants.RABBIT_HOST,
                                           heartbeat_interval=600,
                                           blocked_connection_timeout=300)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=constants.EXCHANGE_NAME, exchange_type='topic')
        self.get_game_queues()

    def get_game_queues(self):
        queues = self.rabbitmq_client.queue.get_queues('game')
        self.queues = list(map(lambda x: x['name'], queues))
        for queue in self.queues:
            self.routing_keys.append(self.rabbitmq_client.queue.get_queue_bindings(queue, constants.EXCHANGE_NAME))

    def get_custom_queues(self):
        return self.rabbitmq_client.queue.get_queues('_')

    def get_queue_bindings(self, queue):
        return self.rabbitmq_client.queue.get_queue_bindings(queue)

    def create_queue(self, queue):
        self.channel.queue_declare(queue=queue, durable=True)
        self.queues.append(queue)

    def create_binding(self, queue, routing_key):
        self.channel.queue_bind(exchange=constants.EXCHANGE_NAME, queue=queue, routing_key=routing_key)
        self.routing_keys.append(routing_key)

    def delete_queue(self, queue, routing_key=''):
        if queue[0] != '_' and queue not in self.queues:
            print('Queue "%s" is not is queue list' % queue)
            return
        if not routing_key:
            routing_key = self.get_queue_bindings(queue)
        self.channel.queue_delete(queue=queue)
        self.queues.remove(queue)
        self.routing_keys.remove(routing_key)

    def add_tasks_game(self, game, total_tasks=constants.TASKS_GAME):
        print('Start add tasks game = %s' % game)
        self.game = game
        routing_key = params_to_routing_key(game)
        if routing_key not in self.routing_keys:
            queue = params_to_queue_name(game)
            self.create_queue(queue)
            self.create_binding(queue, routing_key)
        self.add_tasks(routing_key, total_tasks)

    def add_tasks_custom(self, game, user, streamer='', total_tasks=constants.TASKS_CUSTOM):
        self.game = game
        self.streamer = streamer
        self.user = user
        if streamer:
            routing_key = params_to_routing_key(game, streamer, user)
            queue = params_to_queue_name(game, streamer, user)
        else:
            routing_key = params_to_routing_key(game, user=user)
            queue = params_to_queue_name(game, user=user)
        self.create_queue(queue)
        self.create_binding(queue, routing_key)
        self.add_tasks(routing_key, total_tasks)

    def add_candidates(self, candidates, video_twid, routing_key):
        print('Adding candidates using routing key = %s' % routing_key)
        for candidate in candidates:
            message = self.candidate_to_message(candidate, video_twid)
            self.channel.basic_publish(exchange=constants.EXCHANGE_NAME,
                                       routing_key=routing_key,
                                       body=message)

    # TODO: Add tasks should pass game and streamer to get_new_video
    def add_tasks(self, routing_key, total_tasks):
        print('Start add tasks with routing key = %s' % routing_key)
        new_tasks = 0
        print('Total tasks requested %d' % total_tasks)
        game, streamer, user = routing_key_to_params(routing_key)
        print('Params from routing key game = %s, streamer = %s, user = %s' % (game, streamer, user))
        while new_tasks < total_tasks:
            video = self.twitch_video.get_new_video(self.game, self.streamer)
            if not video:
                print('There was an error getting a new video')
                break
            if not settings.NO_CELERY:
                self.twitch_video.post_video_repit_data(video)
            video_twid = video['id'].replace('v', '')
            print('Got video = %s' % video_twid)
            twitch_chat = TwitchChat(video_twid, self.twitch_video.settings['client_id'])
            twitch_highlight = TwitchHighlight(twitch_chat.get_messages_timestamp())
            candidates = twitch_highlight.get_candidates()
            print('Got %d candidates' % len(candidates))
            self.add_candidates(candidates, video_twid, routing_key)
            print('New Tasks = ', new_tasks)
            if new_tasks == 0:
                print('Before _update_queue_jobs_available')
                self.update_queue_jobs_available(self.game, self.streamer or streamer, self.user or user)
            new_tasks += len(candidates)
        return

    def update_queue_jobs_available(self, game, streamer, user):
        print('in _update_queue_jobs_available')
        print('game = %s, streamer = %s, user = %s' % (game, streamer, user))
        data = {'jobs_available': True}
        if user:
            response = self.update_custom_queue_status(game, streamer, user, data)
        else:
            response = self.update_game_queue_status(game, data)
        return response

    def clear_custom_queue(self, queue):
        routing_key = self.get_queue_bindings(queue['name'])
        game, _, _ = routing_key_to_params(routing_key)
        game_queue = params_to_queue_name(game)
        game_routing_key = params_to_routing_key(game)
        tasks_left = True
        if game_queue not in self.queues:
            self.create_queue(game_queue)
        while tasks_left:
            method, _, body = self.channel.basic_get(queue=queue['name'])
            if not method or method.NAME == 'Basic.GetEmpty':
                break
            self.channel.basic_ack(delivery_tag=method.delivery_tag)
            self.channel.basic_publish(exchange=constants.EXCHANGE_NAME, routing_key=game_routing_key, body=body)
            tasks_left = method.message_count > 0
        self.delete_queue(queue['name'])
        return

    def clear_all_custom_queue(self):
        queues = self.get_custom_queues()
        for queue in queues:
            self.clear_custom_queue(queue)

    def get_job(self, game, streamer, user):
        queue = params_to_queue_name(game, streamer, user)
        method, _, body = self.channel.basic_get(queue=queue)
        if not method or method.NAME == 'Basic.GetEmpty':
            return 'EMPTY'
        task = pickle.loads(body)
        task['st_time'] = str(task['st_time'])
        task['end_time'] = str(task['end_time'])
        task['delivery_tag'] = str(method.delivery_tag)
        return task

    def ack_task(self, delivery_tag):
        self.channel.basic_ack(delivery_tag=delivery_tag)
        return {'status': 'SUCCEED'}

    def get_game_streamers(self, game, limit=10):
        streamers = self.twitch_video.twitch_client.client.streams.get_live_streams(game=game, language='en')
        streamers = list(filter(lambda x: x['channel']['broadcaster_language'] == 'en', streamers))
        streamers = list(map(lambda x: x['channel']['name'], streamers))
        return streamers[:limit] if len(streamers) > limit else streamers

    def close_connection(self):
        if self.connection:
            self.connection.close()

    @staticmethod
    def _get_game_queues_status():
        response = requests.get(constants.GAME_QUEUE_ENDPOINT)
        if response.status_code != status.HTTP_200_OK:
            return None
        return response.json()

    def update_game_queue_status(self, game, data):
        print('update_game_queue_status start')
        if game not in self.queues_id:
            queues = self._get_game_queues_status()
            for queue in queues:
                if queue['game'] == game:
                    self.queues_id[game] = queue['id']
                    break
            if game not in self.queues_id:
                print('not found id')
                print('queues = ', queues)
                return False
        url = '%s%s' % (constants.GAME_QUEUE_ENDPOINT, self.queues_id[game])
        data['game'] = game
        print('put request to %s' % url)
        print('data = ', data)
        response = requests.put(url, data=data)
        print('response = ', response)
        return response.status_code == status.HTTP_200_OK

    @staticmethod
    def update_custom_queue_status(game, streamer, user, data):
        params = {
            'game': game,
            'streamer': streamer,
            'user': user,
        }
        response = requests.get(constants.CUSTOM_QUEUE_ENDPOINT, params=params)
        if response.status_code != status.HTTP_200_OK:
            return False
        response_data = response.json()
        if len(response_data) != 1:
            return False
        queue_id = response_data[0]['id']
        url = '%s%s' % (constants.CUSTOM_QUEUE_ENDPOINT, queue_id)
        for key, value in params.items():
            data[key] = value
        response = requests.put(url, data=data)
        return response.status_code == status.HTTP_200_OK

    @staticmethod
    def candidate_to_message(candidate, video_twid):
        message = {
            'video_id': video_twid,
            'st_time': candidate.st,
            'end_time': candidate.end
        }
        return pickle.dumps(message)


class RepitTaskQueue:
    def __init__(self):
        self.rabbitmq_client = RabbitMQClient()

    def get_message_count(self, queue):
        return self.rabbitmq_client.queue.get_queue_message_count(queue)

    def tasks_available(self, queue):
        return self.rabbitmq_client.queue.tasks_available(queue)
