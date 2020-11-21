from datetime import datetime, timedelta
import json
import logging
import re
from typing import Optional, List, Tuple
import uuid

from lunch_buddies.clients.slack import SlackClient, ChannelDoesNotExist
from lunch_buddies.constants import polls, slack
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.models.polls import Poll, Choice
from lunch_buddies.models.teams import Team
from lunch_buddies.types import PollsToStartMessage, UsersToPollMessage

logger = logging.getLogger(__name__)

DEFAULT_CHANNEL_NOT_FOUND = (
    'Error creating poll. When creating a poll via the slash command "/lunch_buddies_create", there must be a channel named "#lunch_buddies", '
    'however that channel could not be found. You can either create a channel named "#lunch_buddies" and try again, or create a poll by inviting "@Lunch Buddies" to any channel '
    'and saying "@Lunch Buddies create"'
)

USER_NOT_IN_DEFAULT_CHANNEL = (
    'Error creating poll. To create a poll via the slash command "/lunch_buddies_create", you must be a member of <#{}|{}>. '
    "You can join that channel and try again."
)


def create_poll(
    message: PollsToStartMessage,
    slack_client: SlackClient,
    polls_dao: PollsDao,
    teams_dao: TeamsDao,
) -> List[UsersToPollMessage]:
    logger.info("Create poll: {} {}".format(message.team_id, message.channel_id))
    team = teams_dao.read_one_or_die("team_id", message.team_id)
    channel_id = message.channel_id or _get_default_channel_id(
        message, slack_client, team
    )
    if not channel_id:
        return []

    poll = polls_dao.find_latest_by_team_channel(message.team_id, channel_id)

    if (
        poll
        and poll.state != polls.CLOSED
        and poll.created_at > (datetime.now() - timedelta(days=1))
    ):
        logger.info(
            "Found the following poll: {}".format(
                json.dumps(poll._asdict(), default=str)
            )
        )
        slack_client.post_message_if_channel_exists(
            bot_access_token=team.bot_access_token,
            channel=message.user_id,
            as_user=True,
            text="There is already an active poll",
        )

        return []

    callback_id = _get_uuid()
    created_at = _get_created_at()

    choices, group_size = parse_message_text(message.text)

    users = slack_client.conversations_members(team.bot_access_token, channel_id)

    poll = Poll(
        team_id=message.team_id,
        created_at=created_at,
        created_by_user_id=message.user_id,
        callback_id=callback_id,
        state=polls.CREATED,
        channel_id=channel_id,
        choices=choices,
        group_size=group_size,
        stripe_invoice_id=None,
    )

    polls_dao.create(poll)

    return [
        UsersToPollMessage(
            team_id=message.team_id, user_id=user_id, callback_id=callback_id
        )
        for user_id in users
    ]


def _get_default_channel_id(
    message: PollsToStartMessage,
    slack_client: SlackClient,
    team: Team,
) -> Optional[str]:
    try:
        default_channel = slack_client.get_channel(
            team.bot_access_token, slack.LUNCH_BUDDIES_CHANNEL_NAME
        )
    except ChannelDoesNotExist:
        slack_client.post_message_if_channel_exists(
            bot_access_token=team.bot_access_token,
            channel=message.user_id,
            as_user=True,
            text=DEFAULT_CHANNEL_NOT_FOUND,
        )

        return None

    channel_id = default_channel.channel_id

    if message.user_id not in slack_client.conversations_members(
        team.bot_access_token, channel_id
    ):
        slack_client.post_message_if_channel_exists(
            bot_access_token=team.bot_access_token,
            channel=message.user_id,
            as_user=True,
            text=USER_NOT_IN_DEFAULT_CHANNEL.format(channel_id, default_channel.name),
        )

        return None

    return channel_id


def _get_uuid() -> uuid.UUID:
    return uuid.uuid4()


def _get_created_at() -> datetime:
    return datetime.now()


class InvalidPollOption(Exception):
    def __init__(self, option: str) -> None:
        super(InvalidPollOption, self).__init__(
            'Option could not be parsed into a time: "{}"'.format(option)
        )


class InvalidPollSize(Exception):
    def __init__(self, size: str) -> None:
        super(InvalidPollSize, self).__init__(
            'Size must be between 2 and 6. Received: "{}"'.format(size)
        )


def parse_message_text(text: str) -> Tuple[List[Choice], int]:
    if not text:
        return polls.CHOICES, polls.DEFAULT_GROUP_SIZE

    text, group_size = _get_group_size_from_text(text)

    options = list(map(lambda o: o.strip(), text.split(",")))

    choices = list(map(get_choice_from_raw_option, options))
    choices.append(
        Choice(
            key="no",
            is_yes=False,
            time="",
            display_text="No",
        )
    )

    return choices, group_size


def _get_group_size_from_text(text: str) -> Tuple[str, int]:
    text = text.strip()
    size_search = re.search(r"(.*)size=(.+)", text)
    if size_search:
        try:
            group_size = int(size_search.group(2))
            if group_size <= 1 or group_size > 6:
                raise InvalidPollSize(str(group_size))
            text = size_search.group(1)
        except ValueError:
            raise InvalidPollSize(size_search.group(2))
    else:
        group_size = polls.DEFAULT_GROUP_SIZE

    return text, group_size


def get_choice_from_raw_option(option: str) -> Choice:
    try:
        int(option)
    except ValueError:
        raise InvalidPollOption(option)

    time = get_time_from_raw_option(option)

    return Choice(
        key="yes_{}".format(option),
        is_yes=True,
        time=time,
        display_text="Yes ({})".format(time),
    )


def get_time_from_raw_option(raw_option: str) -> str:
    hour = int(raw_option[:-2])
    minute = int(raw_option[-2:])

    try:
        datetime(2018, 1, 1, hour, minute)
    except ValueError:
        raise InvalidPollOption(raw_option)

    return "{}:{}".format(hour, str(minute).zfill(2))
