from slackclient import SlackClient as BaseSlackClient


class ChannelDoesNotExist(Exception):
    pass


class SlackClient(object):
    def _get_base_client_for_team(self, team):
        return BaseSlackClient(team.bot_access_token)

    def create_channel(self, team, name, is_private, **kwargs):
        return self._get_base_client_for_team(team).api_call(
            'conversations.create',
            name=name,
            is_private=is_private,
            **kwargs
        )

    def open_conversation(self, team, **kwargs):
        return self._get_base_client_for_team(team).api_call('conversations.open', **kwargs)

    def post_message(self, team, **kwargs):
        return self._get_base_client_for_team(team).api_call('chat.postMessage', **kwargs)

    def _channels_list_internal(self, team):
        return self._get_base_client_for_team(team).api_call('channels.list')

    def _channels_info_internal(self, team, **kwargs):
        return self._get_base_client_for_team(team).api_call('channels.info', **kwargs)

    def _users_info_internal(self, team, **kwargs):
        return self._get_base_client_for_team(team).api_call('users.info', **kwargs)

    def get_channel(self, team, name):
        channels = [
            channel
            for channel in self._channels_list_internal(team)['channels']
            if channel['name'] == name
        ]

        try:
            return channels[0]
        except IndexError:
            raise ChannelDoesNotExist()

    def list_users(self, team, channel_name):
        lunch_buddies_channel = self.get_channel(team, channel_name)

        user_ids_in_channel = self._channels_info_internal(
            team,
            channel=lunch_buddies_channel['id']
        )['channel']['members']

        return [
            self._users_info_internal(team, user=user_id)['user']
            for user_id in user_ids_in_channel
        ]
