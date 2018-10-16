import os
import json
from datetime import time
from repitapi.client import RepitClient
from filler.models import Video
from django.core.serializers.json import DjangoJSONEncoder
from .repit_twitch_api import RepitTwitchAPI


# Class to get videos id of videos that have not been added to db yet
# For now it decides which game and streamer to look based on settings priorities
class TwitchVideo:
    def __init__(self, settings_path=os.path.join(os.getcwd(), 'settings.json')):
        self.repit_twitch_client = RepitClient().twitch_data
        with open(settings_path, 'r') as f:
            self.settings = json.load(f)
        self.twitch_client = RepitTwitchAPI()
        self.game = None
        self.videos = []
        self.twitch_api_limit = 99

    def get_new_video(self):
        video = None
        while video is None:
            if not self.videos:
                self.get_new_videos()
            while self.videos:
                check_video = self.videos.pop(0)
                if not self.past_video(check_video['id'].replace('v', '')):
                    video = check_video
                    break
        Video.objects.create(twid=video['id'].replace('v', ''))
        return video

    @staticmethod
    def past_video(video_id):
        try:
            Video.objects.get(twid=video_id)
            return True
        except Video.DoesNotExist:
            return False

    @staticmethod
    def seconds_to_h_m_s(secs):
        h = int(secs / 3600)
        secs -= h * 3600
        m = int(secs / 60)
        secs -= m * 60
        return {
            'hour': h,
            'minute': m,
            'second': secs
        }

    def post_video_repit_data(self, video):
        data = {
            'twid': video['id'].replace('v', ''),
            'streamer_twid': video['channel']['id'],
            'streamer_name': video['channel']['name'],
            'game_twid': self.game['id'],
            'game_name': video['game'],
            'recorded': json.dumps(video['created_at'], cls=DjangoJSONEncoder),
            'length': json.dumps(time(**self.seconds_to_h_m_s(video['length'])), cls=DjangoJSONEncoder)
        }
        return self.repit_twitch_client.video.post_object(data)

    # TODO: Add a way to not check all videos again
    def get_new_videos(self, game, streamer=''):
        self.game = self.get_twitch_game(self.settings['video']['game'])
        for streamer in self.settings['video']['streamer_priorities']:
            offset = 0
            params = {
                'streamer_name': streamer,
                'limit': self.twitch_api_limit,
                'offset': offset,
            }
            videos = self.twitch_client.get_streamer_videos(params)
            # Skip videos which are not from specified game
            videos = list(filter(lambda x: x['game'] == self.settings['video']['game'], videos))
            while videos:
                for i, video in enumerate(videos):
                    video_twid = video['id'].replace('v', '')
                    if self.repit_twitch_client.video.get_objects({'twid': video_twid}):
                        continue
                    self.videos = videos[i:]
                    return
                if len(videos) != self.twitch_api_limit:
                    # If videos retrieved are less than api limit then there are no more videos
                    break
                offset += self.twitch_api_limit
                params['offset'] = offset
                videos = self.twitch_client.get_streamer_videos(params)
                videos = list(filter(lambda x: x['game'] == self.settings['video']['game'], videos))
        return None

    def get_twitch_game(self, game_name):
        games = self.twitch_client.client.games.get_top(limit=100)
        games = list(filter(lambda x: x['game']['name'] == game_name, games))
        if len(games) == 0:
            return None
        return games[0]['game']
