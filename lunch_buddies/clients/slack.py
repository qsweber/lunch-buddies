from typing import List, Tuple

from slackclient import SlackClient as BaseSlackClient


class ChannelDoesNotExist(Exception):
    pass


class SlackClient(object):
    def _get_base_client_for_token(self, token: str):
        return BaseSlackClient(token)

    def open_conversation(self, bot_access_token: str, **kwargs):
        return self._get_base_client_for_token(bot_access_token).api_call(
            "conversations.open", **kwargs
        )

    def post_message(self, bot_access_token: str, **kwargs):
        return self._get_base_client_for_token(bot_access_token).api_call(
            "chat.postMessage", **kwargs
        )

    def _channels_list_internal(self, bot_access_token: str) -> List[dict]:
        base_client = self._get_base_client_for_token(bot_access_token)
        return base_client.api_call("conversations.list")["channels"]

    def _channel_members(self, bot_access_token: str, channel_id: str) -> List[str]:
        base_client = self._get_base_client_for_token(bot_access_token)
        result = base_client.api_call("conversations.members", channel=channel_id)
        if not result["ok"]:
            raise ChannelDoesNotExist()

        return result["members"]

    def _users_info_internal(self, bot_access_token: str, **kwargs) -> dict:
        return self._get_base_client_for_token(bot_access_token).api_call(
            "users.info", **kwargs
        )

    def get_channel(self, bot_access_token: str, name: str) -> dict:
        channels = [
            channel
            for channel in self._channels_list_internal(bot_access_token)
            if channel["name"] == name
        ]

        try:
            return channels[0]
        except IndexError:
            raise ChannelDoesNotExist()

    def list_users(self, bot_access_token: str, channel_id: str) -> List[str]:
        return self._channel_members(bot_access_token, channel_id=channel_id)

    def get_user_tz(self, bot_access_token: str, user_id: str) -> str:
        user_info = self._users_info_internal(bot_access_token, user=user_id)

        return user_info["user"]["tz"]

    def get_user_name_email(
        self, bot_access_token: str, user_id: str
    ) -> Tuple[str, str]:
        user_info = self._users_info_internal(bot_access_token, user=user_id)

        return (
            user_info["user"]["profile"]["real_name"],
            user_info["user"]["profile"]["email"],
        )
