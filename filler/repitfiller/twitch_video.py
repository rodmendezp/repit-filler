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
        self.min_length = 600  # in seconds
        self.max_length = 24 * 60 * 60

    def get_new_video(self, game, streamer):
        video = None
        while video is None:
            if not self.videos or self.different_game_streamer(game, streamer):
                self.videos = self.get_new_videos(game, streamer)
            while self.videos:
                print('Checking videos')
                check_video = self.videos.pop(0)
                if not self.past_video(check_video['id'].replace('v', '')):
                    Video.objects.create(twid=check_video['id'].replace('v', ''))
                    return check_video
        raise NoVideosException

    def different_game_streamer(self, game, streamer):
        return self.video_info['game'] != game or self.video_info['streamer'] != streamer

    @staticmethod
    def past_video(video_id):
        try:
            Video.objects.get(twid=video_id)
            print('Video %s is already in filler video' % video_id)
            return True
        except Video.DoesNotExist:
            print('Video %s is not in filler video' % video_id)
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
        print('posting video %s to repit twitchdata' % video['id'].replace('v', ''))
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
        skip_games = ['Just Chatting', 'Poker', 'Casino']
        print('Getting random top game')
        limit = 10
        games = self.get_twitch_games(limit)
        game = None
        while game is None:
            randint = random.randint(0, limit - 1)
            if games[randint] in skip_games:
                continue
            game = games[randint]
        return game

    def get_random_top_streamer(self, game, limit=5):
        print('Getting random top streamer')
        streamers = None
        offset = 0
        while not streamers:
            streamers = self.twitch_client.client.streams.get_live_streams(game=game, limit=limit,
                                                                           language='en', offset=offset)
            if len(streamers) == 0:
                raise NoStreamerException
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
            print('Got random streamer %s' % streamer)
        videos = None
        last_videos = None
        offset = 0
        limit = 100
        params = {
            'streamer_name': streamer,
            'limit': limit,
        }
        break_loop = False
        while videos is None or len(videos) == 0:
            params['offset'] = offset
            print('Getting streamer videos')
            videos = self.twitch_client.get_streamer_videos(params)
            print('total videos before filter = %d' % len(videos))
            if (last_videos and last_videos == videos) or len(videos) == 0:
                break
            if len(videos) != limit:
                break_loop = True
            videos = list(filter(lambda x: x['length'] > self.min_length, videos))
            print('total videos after len (> 10 min) filter = %d' % len(videos))
            videos = list(filter(lambda x: x['lenght'] < self.max_length, videos))
            print('total videos after len (< 24 hrs) filter = %d' % len(videos))
            videos = list(filter(lambda x: x['game'] == game, videos))
            print('total videos after game filter = %d' % len(videos))
            videos = list(filter(lambda x: x['status'] != 'recording', videos))
            print('total videos after recording filter = %d' % len(videos))
            videos = list(filter(lambda x: not self.twitch_client.is_video_restricted(x['id'].replace('v', '')), videos))
            print('total videos after restricted filter = %d' % len(videos))
            if not settings.NO_CELERY:
                videos = self.remove_existing_videos(videos)
            if break_loop:
                break
            offset += limit
            last_videos = videos
        self.video_info['game'] = game
        self.video_info['streamer'] = streamer
        if not videos:
            raise NoVideosException
        return videos

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


class NoStreamerException(Exception):
    pass


class NoVideosException(Exception):
    pass
