import os

from slackclient import SlackClient as BaseSlackClient


class SlackClient(object):
    def __init__(self):
        self.baseClient = BaseSlackClient(os.environ['SLACK_API_TOKEN'])

    def open_conversation(self, **kwargs):
        return self.baseClient.api_call('conversations.open', **kwargs)

    def post_message(self, **kwargs):
        return self.baseClient.api_call('chat.postMessage', **kwargs)

    def _channels_list_internal(self):
        return self.baseClient.api_call('channels.list')

    def _channels_info_internal(self, **kwargs):
        return self.baseClient.api_call('channels.info', **kwargs)

    def _users_info_internal(self, **kwargs):
        return self.baseClient.api_call('users.info', **kwargs)

    def list_users(self, channel_name):
        lunch_buddies_channel = [
            channel
            for channel in self._channels_list_internal()['channels']
            if channel['name'] == channel_name
        ][0]

        user_ids_in_channel = self._channels_info_internal(channel=lunch_buddies_channel['id'])['channel']['members']

        return [
            self._users_info_internal(user=user_id)['user']
            for user_id in user_ids_in_channel
        ]
