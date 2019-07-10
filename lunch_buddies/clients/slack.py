from typing import List

from slack import WebClient as BaseSlackClient

from lunch_buddies.models.teams import Team


class ChannelDoesNotExist(Exception):
    pass


class SlackClient(object):
    def _get_base_client_for_team(self, token: str):
        return BaseSlackClient(token)

    def open_conversation(self, team: Team, **kwargs):
        return self._get_base_client_for_team(team.bot_access_token).api_call(api_method='conversations.open', json=kwargs)

    def post_message(self, team: Team, **kwargs):
        return self._get_base_client_for_team(team.bot_access_token).api_call(api_method='chat.postMessage', json=kwargs)

    def _channels_list_internal(self, team: Team) -> List[dict]:
        base_client = self._get_base_client_for_team(team.bot_access_token)
        return base_client.api_call(api_method='groups.list')['groups'] + base_client.api_call(api_method='channels.list')['channels']

    def _channels_info_internal(self, team: Team, **kwargs) -> dict:
        channel_info = self._get_base_client_for_team(team.bot_access_token).api_call(api_method='channels.info', json=kwargs)
        if channel_info['ok']:
            return channel_info['channel']
        else:
            group_info = self._get_base_client_for_team(team.bot_access_token).api_call(api_method='groups.info', json=kwargs)

            if group_info['ok']:
                return group_info['group']

        raise ChannelDoesNotExist()

    def _users_info_internal(self, team: Team, **kwargs) -> dict:
        return self._get_base_client_for_team(team.bot_access_token).api_call(api_method='users.info', json=kwargs)

    def get_channel(self, team: Team, name: str) -> dict:
        channels = [
            channel
            for channel in self._channels_list_internal(team)
            if channel['name'] == name
        ]

        try:
            return channels[0]
        except IndexError:
            raise ChannelDoesNotExist()

    def list_users(self, team: Team, channel_id: str) -> List[str]:
        return self._channels_info_internal(
            team,
            channel=channel_id
        )['members']

    def get_user_tz(self, team: Team, user_id: str) -> str:
        user_info = self._users_info_internal(team, user=user_id)

        return user_info['user']['tz']
