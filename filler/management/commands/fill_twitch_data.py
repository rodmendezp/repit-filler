import os
import json
from datetime import time
from django.conf import settings
from repitapi.client import RepitClient
from django.core.management.base import BaseCommand
from filler.repitfiller.twitch_chat import TwitchChat
from filler.repitfiller.twitch_video import TwitchVideo
from django.core.serializers.json import DjangoJSONEncoder

CHAT_FOLDER = 'D:\\Rodrigo\\Programming\\Projects\\repititfiller\\output\\'


class Command(BaseCommand):
    help = ''

    def __init__(self, stdout=None, stderr=None, no_color=False):
        self.twitch_video = TwitchVideo()
        self.repit_client = RepitClient()
        super().__init__(stdout, stderr, no_color)

    def add_arguments(self, parser):
        super().add_arguments(parser)

    def handle(self, *args, **options):
        streamer_folders = os.listdir(CHAT_FOLDER)
        for streamer_folder in streamer_folders:
            chats = os.listdir(CHAT_FOLDER + streamer_folder)
            for chat in chats:
                video_id = chat.replace('v', '').replace('.txt', '')
                if self.check_video_chat_data(video_id):
                    continue
                video = self.get_or_create_video(video_id)
                twitch_chat = TwitchChat(video_id, settings.TWITCH_CLIENT_ID,
                                         os.path.join(CHAT_FOLDER, streamer_folder, chat))
                twitch_chat.add_to_repit_twitch_data()

    def check_video_chat_data(self, video_twid):
        chat = self.repit_client.twitch_data.chat.get_objects({'video__twid': video_twid})
        if not chat or len(chat) == 0:
            return False
        elif len(chat) == 1:
            return True
        return None

    def get_or_create_video(self, video_twid):
        video = self.repit_client.twitch_data.video.get_objects({'twid': video_twid})
        if video and len(video) == 1:
            return video[0]
        video = self.twitch_video.twitch_client.client.videos.get_by_id(video_twid)
        game_twid = self.twitch_video.get_twitch_game_id(video['game'])
        data = {
            'twid': video_twid,
            'streamer_twid': video['channel']['id'],
            'streamer_name': video['channel']['name'],
            'game_twid': game_twid,
            'game_name': video['game'],
            'recorded': json.dumps(video['created_at'], cls=DjangoJSONEncoder),
            'length': json.dumps(time(**self.twitch_video.seconds_to_h_m_s(video['length'])), cls=DjangoJSONEncoder)
        }
        return self.repit_client.twitch_data.video.post_object(data)

