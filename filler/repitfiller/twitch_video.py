import os
import json
import random
from datetime import time
from filler.models import Video
from repitapi.client import RepitClient
from django.conf import settings
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
        self.videos = []
        self.video_info = {
            'game': None,
            'streamer': None,
        }
        self.twitch_api_limit = 10

    def get_new_video(self, game, streamer):
        video = None
        while video is None:
            if not self.videos or (self.video_info['game'] != game and self.video_info['streamer']):
                self.get_new_videos(game, streamer)
            while self.videos:
                print('Checking videos')
                check_video = self.videos.pop(0)
                if not self.past_video(check_video['id'].replace('v', '')):
                    Video.objects.create(twid=check_video['id'].replace('v', ''))
                    return check_video
        return None

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
            'game_twid': self.get_twitch_game_id(self.video_info['game']),
            'game_name': self.video_info['game'],
            'recorded': json.dumps(video['created_at'], cls=DjangoJSONEncoder),
            'length': json.dumps(time(**self.seconds_to_h_m_s(video['length'])), cls=DjangoJSONEncoder)
        }
        return self.repit_twitch_client.video.post_object(data)

    def get_random_top_game(self):
        print('Getting random top game')
        limit = 10
        games = self.get_twitch_games(limit)
        game = None
        while game is None:
            randint = random.randint(0, limit - 1)
            if games[randint] == 'Just Chatting':
                continue
            game = games[randint]
        return game

    def get_random_top_streamer(self, game, limit=10):
        print('Getting random top streamer')
        streamers = None
        offset = 0
        while not streamers:
            streamers = self.twitch_client.client.streams.get_live_streams(game=game, limit=limit,
                                                                           language='en', offset=offset)
            if len(streamers) == 0:
                print('Something went wrong, did not found streamers')
                break
            streamers = list(filter(lambda x: x['channel']['broadcaster_language'] == 'en', streamers))
            offset += limit
        randint = random.randint(0, len(streamers) - 1)
        return streamers[randint]['channel']['name']

    def get_new_videos(self, game=None, streamer=None):
        print('Getting new videos for game %s and streamer %s' % (game, streamer))
        if not game:
            game = self.get_random_top_game()
            print('Got random game %s' % game)
        if not streamer:
            streamer = self.get_random_top_streamer(game)
            print('Got random streamer %s')
        videos = None
        offset = 0
        params = {
            'streamer_name': streamer,
            'limit': self.twitch_api_limit,
        }
        break_loop = False
        while videos is None or len(videos) == 0:
            params['offset'] = offset
            videos = self.twitch_client.get_streamer_videos(params)
            if len(videos) != self.twitch_api_limit:
                break_loop = True
            videos = list(filter(lambda x: x['game'] == game, videos))
            # videos = list(filter(lambda x: x['length'] <= 3600, videos))
            videos = list(filter(lambda x: x['status'] != 'recording', videos))
            if not settings.NO_CELERY:
                videos = self.remove_existing_videos(videos)
            if break_loop:
                break
            offset += self.twitch_api_limit
        self.videos = videos
        self.video_info['game'] = game
        self.video_info['streamer'] = streamer
        return

    def remove_existing_videos(self, videos):
        i = 0
        while i < len(videos):
            video_twid = videos[i]['id'].replace('v', '')
            if self.repit_twitch_client.video.get_objects({'twid': video_twid}):
                videos.pop(i)
            else:
                i += 1
        return videos

    def get_twitch_game(self, game_name):
        games = self.get_twitch_games()
        game = list(filter(lambda x: x == game_name, games))
        return game[0] if len(game) == 1 else None

    def get_twitch_game_id(self, game_name):
        games = self.twitch_client.client.games.get_top(limit=100)
        games = list(filter(lambda x: x['game']['name'] == game_name, games))
        return games[0]['game']['id'] if len(games) == 1 else None

    def get_twitch_games(self, limit=100):
        games = self.twitch_client.client.games.get_top(limit=limit)
        games = list(map(lambda x: x['game']['name'], games))
        return games
