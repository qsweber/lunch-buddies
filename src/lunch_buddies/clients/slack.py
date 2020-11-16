from typing import cast, Any, List, NamedTuple

from slack_sdk import WebClient as BaseSlackClient


class ChannelDoesNotExist(Exception):
    pass


class PostMessageResponse(NamedTuple):
    ts: str


class OpenConversationResponse(NamedTuple):
    channel_id: str


class Channel(NamedTuple):
    channel_id: str
    name: str


class User(NamedTuple):
    name: str
    email: str
    tz: str


class SlackClient(object):
    def _get_base_client_for_token(self, token: str) -> BaseSlackClient:
        return BaseSlackClient(token)

    def open_conversation(
        self, bot_access_token: str, **kwargs: Any
    ) -> OpenConversationResponse:
        base_client = self._get_base_client_for_token(bot_access_token)
        response = base_client.conversations_open(**kwargs)
        return OpenConversationResponse(channel_id=response.get("channel")["id"])

    def post_message(
        self,
        bot_access_token: str,
        channel: str,
        as_user: bool,
        text: str,
        **kwargs: Any
    ) -> PostMessageResponse:
        base_client = self._get_base_client_for_token(bot_access_token)
        response = base_client.chat_postMessage(
            channel=channel, as_user=as_user, text=text, **kwargs
        )
        return PostMessageResponse(ts=response.get("ts"))

    def _channels_list_internal(self, bot_access_token: str) -> List[Channel]:
        base_client = self._get_base_client_for_token(bot_access_token)
        response = base_client.conversations_list()
        return [
            Channel(channel_id=channel["id"], name=channel["name"])
            for channel in response.get("channels")
        ]

    def conversations_members(
        self, bot_access_token: str, channel_id: str
    ) -> List[str]:
        base_client = self._get_base_client_for_token(bot_access_token)
        result = base_client.conversations_members(channel=channel_id)
        if not result.get("ok"):
            raise ChannelDoesNotExist()

        return [cast(str, member) for member in result.get("members")]

    def get_user_info(self, bot_access_token: str, user_id: str) -> User:
        base_client = self._get_base_client_for_token(bot_access_token)
        response = base_client.users_info(user=user_id)
        return User(
            name=response.get("user").get("profile").get("real_name"),
            email=response.get("user").get("profile").get("email"),
            tz=response.get("user").get("tz"),
        )

    def get_channel(self, bot_access_token: str, name: str) -> Channel:
        channels = [
            channel
            for channel in self._channels_list_internal(bot_access_token)
            if channel.name == name
        ]

        try:
            return channels[0]
        except IndexError:
            raise ChannelDoesNotExist()
