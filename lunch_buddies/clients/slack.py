import os

from slackclient import SlackClient as BaseSlackClient


class SlackClient(object):
    def __init__(self):
        self.baseClient = BaseSlackClient(os.environ['SLACK_API_TOKEN'])

    def open_conversation(self, **kwargs):
        return self.baseClient.api_call('conversations.open', **kwargs)

    def post_message(self, **kwargs):
        return self.baseClient.api_call('chat.postMessage', **kwargs)

    def list_users(self):
        result = self.baseClient.api_call(
            'users.list',
        )

        return result['members']