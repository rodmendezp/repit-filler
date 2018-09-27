import os
import json
from repitapi.client import RepitClient
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
        self.twitch_api_limit = 99

    def get_new_video_id(self):
        video_id = None
        while video_id is None:
            if self.videos:
                video_id = self.videos.pop(0)['id'].replace('v', '')
                while self.video_already_exist(video_id) and self.videos:
                    video_id = self.videos.pop(0)['id'].replace('v', '')
            if not video_id:
                self.get_new_videos()
        return video_id

    def video_already_exist(self, video_id):
        return self.repit_twitch_client.video.get_objects({'twid': video_id}) != []

    # TODO: Add a way to not check all videos again
    def get_new_videos(self):
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
