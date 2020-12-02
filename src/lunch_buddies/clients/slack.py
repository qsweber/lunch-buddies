import logging
from typing import cast, Any, List, NamedTuple, Optional

from slack_sdk import WebClient as BaseSlackClient
from slack_sdk.errors import SlackApiError


logger = logging.getLogger(__name__)


class ChannelDoesNotExist(Exception):
    channel_id: str

    def __init__(self, channel_id: str) -> None:
        self.channel_id = channel_id
        super(ChannelDoesNotExist, self).__init__(
            "{} does not exist".format(channel_id)
        )


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
        thread_ts: Optional[str] = None,
        attachments: Optional[Any] = None,
    ) -> PostMessageResponse:
        base_client = self._get_base_client_for_token(bot_access_token)
        try:
            response = base_client.chat_postMessage(
                channel=channel,
                as_user=as_user,
                text=text,
                thread_ts=thread_ts,
                attachments=attachments,
            )
            return PostMessageResponse(ts=response.get("ts"))
        except SlackApiError as err:
            if err.response.data.get("error") == "channel_not_found":
                raise ChannelDoesNotExist(channel)
            raise err

    def post_message_if_channel_exists(
        self,
        bot_access_token: str,
        channel: str,
        as_user: bool,
        text: str,
        thread_ts: Optional[str] = None,
        attachments: Optional[Any] = None,
    ) -> Optional[PostMessageResponse]:
        try:
            return self.post_message(
                bot_access_token, channel, as_user, text, thread_ts, attachments
            )
        except ChannelDoesNotExist as error:
            logger.error(
                "Could not send message to non-existant channel {}".format(
                    error.channel_id
                )
            )
            return None

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
            raise ChannelDoesNotExist(channel_id)

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
            raise ChannelDoesNotExist(name)
