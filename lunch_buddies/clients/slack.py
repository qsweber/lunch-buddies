from slackclient import SlackClient as BaseSlackClient


class SlackClient(object):
    def _get_base_client_for_team(self, team):
        return BaseSlackClient(team.bot_access_token)

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

    def list_users(self, team, channel_name):
        lunch_buddies_channel = [
            channel
            for channel in self._channels_list_internal(team)['channels']
            if channel['name'] == channel_name
        ][0]

        user_ids_in_channel = self._channels_info_internal(
            team,
            channel=lunch_buddies_channel['id']
        )['channel']['members']

        return [
            self._users_info_internal(team, user=user_id)['user']
            for user_id in user_ids_in_channel
        ]
