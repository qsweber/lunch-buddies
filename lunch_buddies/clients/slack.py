from typing import List, Tuple

from slackclient import SlackClient as BaseSlackClient

from lunch_buddies.models.teams import Team


class ChannelDoesNotExist(Exception):
    pass


class SlackClient(object):
    def _get_base_client_for_team(self, token: str):
        return BaseSlackClient(token)

    def open_conversation(self, team: Team, **kwargs):
        return self._get_base_client_for_team(team.bot_access_token).api_call('conversations.open', **kwargs)

    def post_message(self, team: Team, **kwargs):
        return self._get_base_client_for_team(team.bot_access_token).api_call('chat.postMessage', **kwargs)

    def _channels_list_internal(self, team: Team) -> List[dict]:
        base_client = self._get_base_client_for_team(team.bot_access_token)
        return base_client.api_call('conversations.list')['channels']

    def _channel_members(self, team: Team, channel_id: str) -> List[str]:
        base_client = self._get_base_client_for_team(team.bot_access_token)
        result = base_client.api_call('conversations.members', channel=channel_id)
        if not result['ok']:
            raise ChannelDoesNotExist()

        return result['members']

    def _users_info_internal(self, team: Team, **kwargs) -> dict:
        return self._get_base_client_for_team(team.bot_access_token).api_call('users.info', **kwargs)

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
        return self._channel_members(
            team,
            channel_id=channel_id
        )

    def get_user_tz(self, team: Team, user_id: str) -> str:
        user_info = self._users_info_internal(team, user=user_id)

        return user_info['user']['tz']

    def get_user_name_email(self, team: Team, user_id: str) -> Tuple[str, str]:
        user_info = self._users_info_internal(team, user=user_id)

        return user_info['user']['profile']['real_name'], user_info['user']['profile']['email']
