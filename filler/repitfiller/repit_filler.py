import pika
import pickle
from .twitch_chat import TwitchChat
from .twitch_video import TwitchVideo
from .twitch_highlight import TwitchHighlight


'''

'''
# This service use two channels to operate
# 1) Request Channel: It is used to ask for more jobs. Once the queue inside the request channel has a message
# it will get the message and produce at least the number of jobs requested
# 2) Jobs Channel: It is used to post jobs in a queue which are going to be consumed by the Repit app


class RepitFiller:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.request_channel = None
        self.request_channel_id = 1
        self.request_queue_name = 'requested_jobs'
        self.request_queue = None
        self.jobs_channel = None
        self.jobs_channel_id = 2
        self.jobs_queue_name = 'jobs'
        self.jobs_queue = None
        self.collecting_jobs = False
        self.initial_jobs = 0
        self.twitch_chat = None
        self.twitch_video = TwitchVideo()
        self.twitch_highlight = None

    def init_request(self):
        self.request_channel = self.connection.channel(self.request_channel_id)
        self.request_queue = self.request_channel.queue_declare(queue=self.request_queue_name, durable=True)
        self.request_channel.basic_consume(self.request_channel_callback, queue=self.request_queue_name, no_ack=False)

    def init_jobs(self):
        self.jobs_channel = self.connection.channel(self.jobs_channel_id)
        self.jobs_queue = self.jobs_channel.queue_declare(queue=self.jobs_queue_name, durable=True)

    def request_channel_callback(self, ch, method, properties, body):
        if self.collecting_jobs:
            return
        self.collecting_jobs = True
        self.initial_jobs = self.jobs_queue.method.message_count
        body_pickle = pickle.loads(body)
        self.add_jobs(body_pickle['n_jobs'])

    def delete_queues(self):
        if not self.jobs_channel:
            self.init_jobs()
        if not self.request_channel:
            self.init_request()
        self.jobs_channel.queue_delete(queue=self.jobs_queue_name)
        self.request_channel.queue_delete(queue=self.request_queue_name)

    def add_jobs(self, n_jobs):
        print('in add job')
        added_jobs = 0
        while added_jobs < n_jobs:
            video_id = self.twitch_video.get_new_video_id()
            if not video_id:
                print('There was an error getting a new video_id')
                break
            self.twitch_chat = TwitchChat(video_id, self.twitch_video.settings['client_id'])
            self.twitch_highlight = TwitchHighlight(self.twitch_chat.get_messages_timestamp())
            candidates = self.twitch_highlight.get_candidates()
            for candidate in candidates:
                message = {
                    'video_id': video_id,
                    'st_time': candidate.st,
                    'end_time': candidate.end
                }
                message = pickle.dumps(message)
                self.jobs_channel.basic_publish(exchange='',
                                                routing_key=self.jobs_queue_name,
                                                body=message)
                added_jobs += 1
        self.collecting_jobs = False

    def run(self):
        self.request_channel.start_consuming()



