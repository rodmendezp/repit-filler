import pika
import pickle
import requests
from rest_framework import status

from . import constants
from .twitch_chat import TwitchChat
from .twitch_video import TwitchVideo
from .twitch_highlight import TwitchHighlight
from .rabbitmq_api.client import RabbitMQClient


class RepitFiller:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queues = []
        self.queues_id = {}
        self.routing_keys = []
        self.rabbitmq_client = RabbitMQClient()
        self.twitch_video = TwitchVideo()

    def init(self):
        print('IN INIT RepitFiller')
        params = pika.ConnectionParameters(host=constants.RABBIT_HOST,
                                           heartbeat_interval=600,
                                           blocked_connection_timeout=300)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=constants.EXCHANGE_NAME, exchange_type='topic')
        self._get_game_queues()

    def _get_game_queues(self):
        queues = self.rabbitmq_client.queue.get_queues('game')
        self.queues = list(map(lambda x: x['name'], queues))
        for queue in self.queues:
            self.routing_keys.append(self.rabbitmq_client.queue.get_queue_bindings(queue, constants.EXCHANGE_NAME))

    def _get_custom_queues(self):
        return self.rabbitmq_client.queue.get_queues('_')

    def _get_queue_bindings(self, queue):
        return self.rabbitmq_client.queue.get_queue_bindings(queue)

    def _create_queue(self, queue):
        self.channel.queue_declare(queue=queue, durable=True)
        self.queues.append(queue)

    def _create_binding(self, queue, routing_key):
        self.channel.queue_bind(exchange=constants.EXCHANGE_NAME, queue=queue, routing_key=routing_key)
        self.routing_keys.append(routing_key)

    def _delete_queue(self, queue, routing_key=''):
        if queue not in self.queues:
            print('Queue "%s" is not is queue list' % queue)
            return
        if not routing_key:
            routing_key = self._get_queue_bindings(queue)
        self.channel.queue_delete(queue=queue)
        self.queues.remove(queue)
        self.routing_keys.remove(routing_key)

    def add_tasks_game(self, game, total_tasks=constants.TASKS_GAME):
        print('Start add tasks game = %s' % game)
        routing_key = self.params_to_routing_key(game)
        if routing_key not in self.routing_keys:
            queue = self.params_to_queue_name(game)
            self._create_queue(queue)
            self._create_binding(queue, routing_key)
            # response = self._post_game_queue_status(game)
            # if response.status_code == status.HTTP_201_CREATED:
            #     self.queues_id[queue] = response.json()['id']
        self._add_tasks(routing_key, total_tasks)

    def add_tasks_custom(self, game, user, streamer='', total_tasks=constants.TASKS_CUSTOM):
        if streamer:
            routing_key = self.params_to_routing_key(game, streamer, user)
            queue = self.params_to_queue_name(game, streamer, user)
        else:
            routing_key = self.params_to_routing_key(game, user=user)
            queue = self.params_to_queue_name(game, user=user)
        self._create_queue(queue)
        self._create_binding(routing_key, queue)
        # self._post_custom_queue_status(game, streamer, user)
        self._add_tasks(routing_key, total_tasks)

    def _add_candidates(self, candidates, video_twid, routing_key):
        print('Adding candidates using routing key = %s' % routing_key)
        for candidate in candidates:
            message = self.candidate_to_message(candidate, video_twid)
            self.channel.basic_publish(exchange=constants.EXCHANGE_NAME,
                                       routing_key=routing_key,
                                       body=message)

    # TODO: Add tasks should pass game and streamer to get_new_video
    def _add_tasks(self, routing_key, total_tasks):
        print('Start add tasks with routing key = %s' % routing_key)
        new_tasks = 0
        game, streamer, user = self.routing_key_to_params(routing_key)
        while new_tasks < total_tasks:
            video = self.twitch_video.get_new_video()
            if not video:
                print('There was an error getting a new video')
                break
            self.twitch_video.post_video_repit_data(video)
            video_twid = video['id'].replace('v', '')
            print('Got video = %s' % video_twid)
            twitch_chat = TwitchChat(video_twid, self.twitch_video.settings['client_id'])
            twitch_highlight = TwitchHighlight(twitch_chat.get_messages_timestamp())
            candidates = twitch_highlight.get_candidates()
            print('Got %d candidates' % len(candidates))
            self._add_candidates(candidates, video_twid, routing_key)
            print('New Tasks = ', new_tasks)
            if new_tasks == 0:
                print('Before _update_queue_jobs_available')
                self._update_queue_jobs_available(game, streamer, user)
            new_tasks += len(candidates)
        return

    def _update_queue_jobs_available(self, game, streamer, user):
        print('in _update_queue_jobs_available')
        print('game = %s, streamer = %s, user = %s' % (game, streamer, user))
        data = {'jobs_available': True}
        if user:
            response = self.update_custom_queue_status(game, streamer, user, data)
        else:
            response = self.update_game_queue_status(game, data)
        return response

    def _clear_custom_queue(self, queue):
        routing_key = self._get_queue_bindings(queue)
        game, _, _ = self.routing_key_to_params(routing_key)
        game_routing_key = self.params_to_routing_key(game)
        tasks_left = True
        while tasks_left:
            method, _, body = self.channel.basic_get(queue=queue)
            if method.NAME == 'Basic.GetEmpty':
                break
            self.channel.basic_ack(delivery_tag=method.delivery_tag)
            self.channel.basic_publish(exchange=constants.EXCHANGE_NAME, routing_key=game_routing_key, body=body)
            tasks_left = method.message_count > 0
        return

    def _clear_all_custom_queue(self):
        queues = self._get_custom_queues()
        for queue in queues:
            self._clear_custom_queue(queue)

    def get_job(self, game, streamer, user):
        queue = self.params_to_queue_name(game, streamer, user)
        method, _, body = self.channel.basic_get(queue=queue)
        if method.NAME == 'Basic.GetEmpty':
            return 'EMPTY'
        task = pickle.loads(body)
        task['st_time'] = str(task['st_time'])
        task['end_time'] = str(task['end_time'])
        task['delivery_tag'] = str(method.delivery_tag)
        return task

    def _ack_task(self, delivery_tag):
        self.channel.basic_ack(delivery_tag=delivery_tag)
        return {'status': 'SUCCEED'}

    def close_connection(self):
        if self.connection:
            self.connection.close()

    @staticmethod
    def _get_game_queues_status():
        response = requests.get(constants.GAME_QUEUE_ENDPOINT)
        if response.status_code != status.HTTP_200_OK:
            return None
        return response.json()

    # @staticmethod
    # def _game_queue_status_exists(game):
    #     url = '%s?game=%s' % (constants.GAME_QUEUE_ENDPOINT, game)
    #     response = requests.get(url)
    #     if response.status_code == status.HTTP_200_OK:
    #         data = response.json()
    #         return len(data) == 1 and data[0]['game'] == game
    #     else:
    #         print('Error querying game queue (url = %s)' % url)
    #         return False

    # @staticmethod
    # def _post_game_queue_status(game):
    #     data = {'game': game}
    #     response = requests.post(constants.GAME_QUEUE_ENDPOINT, data=data)
    #     return response

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

    # @staticmethod
    # def _post_custom_queue_status(game, streamer, user):
    #     data = {
    #         'game': game,
    #         'streamer': streamer,
    #         'user': user,
    #     }
    #     response = requests.post(constants.CUSTOM_QUEUE_ENDPOINT, data=data)
    #     return response

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

    @staticmethod
    def replace_game_characters(game):
        game = game.replace(' ', '_')
        game = game.replace('-', '_')
        game = game.replace("'", '_')
        game = game.replace(':', '_')
        game = game.replace('__', '_')
        return game.replace('.', '_').lower()

    @staticmethod
    def params_to_queue_name(game, streamer='', user=''):
        game = RepitFiller.replace_game_characters(game)
        if streamer or user:
            queue_name = '_%s_%s_%s' % (user, streamer, game)
        else:
            queue_name = 'game_%s' % game
        return queue_name

    @staticmethod
    def params_to_routing_key(game, streamer='*', user='all'):
        game = RepitFiller.replace_game_characters(game)
        routing_key = '%s.%s.%s' % (game, streamer, user)
        return routing_key

    @staticmethod
    def routing_key_to_params(routing_key):
        first_dot = routing_key.find('.')
        second_dot = routing_key.find('.', first_dot + 1)
        game = routing_key[:first_dot]
        streamer = routing_key[first_dot + 1: second_dot]
        user = routing_key[second_dot + 1:]
        user = '' if user == 'all' else user
        return game, streamer, user


class RepitJobQueue:
    def __init__(self, game, streamer='', user=''):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(constants.RABBIT_HOST))
        self.channel = self.connection.channel()
        self.game = game
        self.streamer = streamer
        self.user = user

    def get_message_count(self):
        queue = RepitFiller.params_to_queue_name(self.game, self.streamer, self.user)
        queue = self.channel.queue_declare(queue=queue, passive=True)
        return queue.method.message_count

    def jobs_available(self):
        return self.get_message_count() > 0

    def close_connection(self):
        if self.connection:
            self.connection.close()
