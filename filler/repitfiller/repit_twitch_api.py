import os
import json
from twitch.client import TwitchClient


class RepitTwitchAPI:
    def __init__(self, settings_path=os.path.join(os.getcwd(), 'settings.json')):
        if os.environ.get('REPIT_SETTINGS', None):
            self.settings_path = os.environ['REPIT_SETTINGS']
        else:
            self.settings_path = settings_path
        with open(self.settings_path, 'r') as f:
            settings = json.load(f)
        self.client = TwitchClient(client_id=settings['client_id'])

    def get_user(self, params):
        user_name = params.get('name', None)
        user_twid = params.get('twid', None)
        if user_name:
            users = self.client.users.translate_usernames_to_ids(user_name)
            if len(users) != 1:
                print('None or Multiple users for a user name')
                return None
            return {
                'name': user_name,
                'twid': users[0]['id']
            }
        elif user_twid:
            user = self.client.users.get_by_id(user_twid)
            return {
                'name': user['name'],
                'twid': user['id']
            }
        print('Need to provide user name or id')
        return None

    def get_streamer(self, streamer_name):
        channels = self.client.search.channels(streamer_name)
        channels = list(filter(lambda x: x['name'] == streamer_name, channels))
        if len(channels) != 1:
            print('None or Multiple channels for a streamer name')
            return None
        twitch_user = self.get_user({'name': streamer_name})
        return {
            'twitch_user': twitch_user,
            'channel': {
                'twid': channels[0]['id']
            }
        }

    def get_game_of_video(self, video_id):
        video = self.get_video(video_id)
        # It is only possible to look for 'top' games
        # Need to iterate with a limit of 99 (max)
        game = None
        offset = 0
        limit = 99
        while not game:
            games = self.client.games.get_top(limit, offset)
            games = list(filter(lambda x: x['game']['name'] == video['game'], games))
            if len(games) == 1:
                game = {
                    'name': games[0]['game']['name'],
                    'twid': games[0]['game']['id']
                }
            if offset > 3 * limit:
                break
            offset += limit
        if not game:
            print('No game was found with the name "%s"' % video['game'])
        return game

    def get_video(self, video_id):
        return self.client.videos.get_by_id(video_id)

    def get_streamer_emoticons(self, streamer_name):
        path = 'channels/{}/product'.format(streamer_name)
        url = 'https://api.twitch.tv/api/'
        response = self.client.channels._request_get(path, url=url)
        emoticon_sets_id = set()
        if not response.get('plans', None):
            return []
        for plan in response['plans']:
            for emoticon_set_id in plan['emoticon_set_ids']:
                emoticon_sets_id.add(emoticon_set_id)
        emoticons = []
        for emoticon_set_id in emoticon_sets_id:
            response = self.client.chat.get_emoticons_by_set(emoticon_set_id)
            emoticon_set = response['emoticon_sets'][str(emoticon_set_id)]
            for emoticon in emoticon_set:
                emoticon['emoticon_set'] = emoticon_set_id
            emoticons += emoticon_set
        return emoticons

    def get_streamer_videos(self, params):
        # Broadcast type archive are the streaming session saved
        channel_twid = params.get('channel_twid', None)
        streamer_name = params.get('streamer_name', None)
        if not channel_twid and not streamer_name:
            print('Need to provide channel id or streamer name')
            return None
        limit = params.get('limit', 10)
        offset = params.get('offset', 0)
        if not channel_twid and streamer_name:
            print('Getting streamer channel id')
            streamer = self.get_streamer(streamer_name)
            channel_twid = streamer['channel']['twid']
            print('Streamer channel id = %d' % channel_twid)
        return self.client.channels.get_videos(channel_twid, limit, offset, 'archive')

    def is_video_restricted(self, video_twid):
        response = self.client.videos._request_get('vods/%s/access_token' % video_twid, url='https://api.twitch.tv/api/')
        token = json.loads(response['token'])
        restricted_bitrates = token['chansub']['restricted_bitrates']
        return restricted_bitrates != []
