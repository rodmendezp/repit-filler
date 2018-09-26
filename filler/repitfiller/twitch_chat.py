import os
import re
from six.moves import xrange
from repitapi.client import RepitClient
from twitchchatdl.app.downloader import download
from .repit_twitch_api import RepitTwitchAPI
from requests.exceptions import ConnectionError, HTTPError


class TwitchChat:
    def __init__(self, video_id, client_id):
        self.video_id = video_id
        self.client_id = client_id
        self.file_name = None
        self.file_path = None
        self.streamer_name = None
        self.repit_twitch_client = RepitClient().twitch_data
        self.twitch_client = RepitTwitchAPI()
        self.messages = []
        self.user_names = set()
        self.twitch_users_db = {}
        self.repit_twitch_data = {}
        self.download()
        self.parse_file()

    def download(self):
        self.file_path = os.path.abspath(download(str(self.video_id), self.client_id))
        self.file_name = os.path.split(self.file_path)[1]
        path, _ = os.path.split(self.file_path)
        self.streamer_name = os.path.split(path)[1]

    def parse_file(self):
        with open(self.file_path, 'r', encoding='utf8') as f:
            for line in f:
                message = Message(line)
                if not message.is_valid():
                    continue
                self.messages.append(message)
                if message.user_name not in self.user_names:
                    self.user_names.add(message.user_name)

    def post_users(self):
        for user_name in self.user_names:
            twitch_users = self.repit_twitch_client.twitch_user.get_objects({'name': user_name})
            if len(twitch_users) > 1:
                print('WARNING: TwitchUser query returned more than 1 result (twitch_user.name = %s)' % user_name)
                continue
            self.twitch_users_db[user_name] = twitch_users[0]
        names_to_add = list(filter(lambda x: x not in self.twitch_users_db.keys(), self.user_names))
        if not names_to_add:
            return
        for user_names_group in chunks(names_to_add, 99):
            try:
                twitch_users = self.twitch_client.client.users.translate_usernames_to_ids(user_names_group)
                for twitch_user in twitch_users:
                    data = {
                        'twid': twitch_user['twid'],
                        'name': twitch_user['name']
                    }
                    new_twitch_user = self.repit_twitch_client.twitch_user.post_object(data)
                    self.twitch_users_db[twitch_user['name']] = new_twitch_user
            except ConnectionError:
                print('There was a ConnectionError')
            except HTTPError:
                print('There was a HTTPError')

    def post_streamer(self):
        streamer = self.twitch_client.get_streamer(self.streamer_name)
        response = self.repit_twitch_client.streamer.post_object(streamer)
        self.repit_twitch_data['streamer'] = response
        return response

    def post_video(self):
        video = self.twitch_client.get_video(self.video_id)
        response = self.repit_twitch_client.video.post_object(video)
        self.repit_twitch_data['video'] = response
        return response

    def post_chat(self):
        chat = {'video': self.repit_twitch_data['video']}
        response = self.repit_twitch_client.chat.post_object(chat)
        self.repit_twitch_data['chat'] = response
        return response

    # TODO: Post multiple objects
    def post_messages(self):
        data = {
            'chat': self.repit_twitch_data['chat'],
            'twitch_user': None,
            'text': None,
            'time': None,
        }
        for message in self.messages:
            repit_twitch_user = self.twitch_users_db.get(message.user_name, None)
            if repit_twitch_user:
                data['twitch_user'] = repit_twitch_user
                data['text'] = message.text
                data['time'] = message.timestamp
                self.repit_twitch_client.message.post_object(data)
        return

    def add_to_repit_twitch_data(self):
        self.post_users()
        self.post_streamer()
        self.post_chat()
        self.post_video()
        self.post_messages()

    def get_messages_timestamp(self):
        return list(map(lambda x: x.timestamp, self.messages))


class Message:
    regex = '\[(\d{1,2}:\d{2}:\d{2})\]\s?\<([^\>]*)\>\s?(.+)'

    def __init__(self, message_text):
        r = re.search(self.regex, message_text)
        if not r:
            print('Invalid message: ', message_text)
            return
        self.timestamp = r.group(1)
        self.user_name = r.group(2)
        self.text = r.group(3)
        self.fix()

    def fix(self):
        self.user_name = self.user_name.replace(' ', '_')

    def is_valid(self):
        # User name will be invalid if it has oriental characters (DB does not support them)
        for c in self.user_name:
            ord_c = ord(c)
            if 0x4e00 <= ord_c <= 0x9fff or 0x30A0 <= ord_c <= 0x30ff or 0xac00 <= ord_c <= 0xd7af:
                return False
        return True


def chunks(seq, size):
    return (seq[pos:pos + size] for pos in xrange(0, len(seq), size))
