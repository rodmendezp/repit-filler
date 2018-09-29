import pika
import pickle
import requests
from datetime import time
from filler.models import Candidate, Video
from .twitch_chat import TwitchChat
from .twitch_video import TwitchVideo
from .twitch_highlight import TwitchHighlight


class RepitFiller:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.jobs_channel = None
        self.jobs_channel_id = 2
        self.jobs_queue_name = 'jobs'
        self.jobs_queue = None
        self.collecting_jobs = False
        self.initial_jobs = 0
        self.twitch_chat = None
        self.twitch_video = TwitchVideo()
        self.twitch_highlight = None

    def init_jobs(self):
        self.jobs_channel = self.connection.channel(self.jobs_channel_id)
        self.jobs_queue = self.jobs_channel.queue_declare(queue=self.jobs_queue_name, durable=True)

    def delete_queue(self):
        if not self.jobs_channel:
            self.init_jobs()
        self.jobs_channel.queue_delete(queue=self.jobs_queue_name)

    def add_jobs(self, n_jobs):
        post_jobs_available = False
        added_jobs = 0
        while added_jobs < n_jobs:
            video = self.twitch_video.get_new_video()
            self.twitch_video.post_video_repit_data(video)
            if not video:
                print('There was an error getting a new video')
                break
            video_twid = video['id'].replace('v', '')
            self.twitch_chat = TwitchChat(video_twid, self.twitch_video.settings['client_id'])
            self.twitch_highlight = TwitchHighlight(self.twitch_chat.get_messages_timestamp())
            candidates = self.twitch_highlight.get_candidates()
            self.post_candidates(candidates, video_twid)
            for candidate in candidates:
                message = {
                    'video_id': video_twid,
                    'st_time': candidate.st,
                    'end_time': candidate.end
                }
                message = pickle.dumps(message)
                self.jobs_channel.basic_publish(exchange='',
                                                routing_key=self.jobs_queue_name,
                                                body=message)
                if not post_jobs_available:
                    post_jobs_available = True
                    requests.put('http://127.0.0.1:9999/filler/jobs_available/', {'jobs_available': True})
                added_jobs += 1
        self.collecting_jobs = False

    def post_candidates(self, candidates, video_twid):
        video = Video.objects.get(twid=video_twid)
        for candidate in candidates:
            st_time = time(**self.twitch_video.seconds_to_h_m_s(int(candidate.st)))
            end_time = time(**self.twitch_video.seconds_to_h_m_s(int(candidate.end)))
            Candidate.objects.create(video=video, start=st_time, end=end_time)

    def get_job(self):
        method_frame, header_frame, body = self.jobs_channel.basic_get(queue=self.jobs_queue_name)
        if method_frame.NAME == 'Basic.GetEmpty':
            self.connection.close()
            return ''
        self.jobs_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        self.connection.close()
        job = pickle.loads(body)
        # TODO: st_time and end_time are numpy int32 therefore not serializable by json in the view
        job['st_time'] = str(job['st_time'])
        job['end_time'] = str(job['end_time'])
        return job


class RepitJobQueue:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.jobs_channel_id = 2
        self.jobs_channel = None

    def jobs_available(self):
        self.jobs_channel = self.connection.channel(self.jobs_channel_id)
        jobs_queue = self.jobs_channel.queue_declare(queue='jobs', passive=True)
        return jobs_queue.method.message_count >= 1

    def close_connection(self):
        self.connection.close()

