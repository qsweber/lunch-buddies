from datetime import datetime
import re
from typing import List, Tuple
import uuid

from lunch_buddies.clients.slack import SlackClient, ChannelDoesNotExist
from lunch_buddies.constants import polls, slack
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.models.polls import Poll, Choice
from lunch_buddies.types import PollsToStartMessage, UsersToPollMessage

DEFAULT_CHANNEL_NOT_FOUND = (
    'Error creating poll. When creating a poll via the slash command "/lunch_buddies_create", there must be a channel named "#lunch_buddies", '
    'however that channel could not be found. You can either create a channel named "#lunch_buddies" and try again, or create a poll by inviting "@Lunch Buddies" to any channel '
    'and saying "@Lunch Buddies create"'
)


def create_poll(
    message: PollsToStartMessage,
    slack_client: SlackClient,
    polls_dao: PollsDao,
    teams_dao: TeamsDao,
) -> List[UsersToPollMessage]:
    team = teams_dao.read('team_id', message.team_id)[0]
    channel_id = message.channel_id
    if not channel_id:
        try:
            lunch_buddies_channel = slack_client.get_channel(team, slack.LUNCH_BUDDIES_CHANNEL_NAME)
        except ChannelDoesNotExist:
            slack_client.post_message(
                team=team,
                channel=message.user_id,
                as_user=True,
                text=DEFAULT_CHANNEL_NOT_FOUND,
            )

            return []

        channel_id = lunch_buddies_channel['id']

    poll = polls_dao.find_latest_by_team_channel(message.team_id, channel_id)

    if poll and poll.state != polls.CLOSED:
        slack_client.post_message(
            team=team,
            channel=message.user_id,
            as_user=True,
            text='There is already an active poll',
        )

        return []

    callback_id = _get_uuid()
    created_at = _get_created_at()

    choices, group_size = parse_message_text(message.text)

    poll = Poll(
        team_id=message.team_id,
        created_at=created_at,
        created_by_user_id=message.user_id,
        callback_id=callback_id,
        state=polls.CREATED,
        channel_id=channel_id,
        choices=choices,
        group_size=group_size,
    )

    polls_dao.create(poll)

    return [
        UsersToPollMessage(team_id=message.team_id, user_id=user_id, callback_id=callback_id)
        for user_id in slack_client.list_users(team, channel_id)
    ]


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

    options = list(map(lambda o: o.strip(), text.split(',')))

    choices = list(map(get_choice_from_raw_option, options))
    choices.append(Choice(
        key='no',
        is_yes=False,
        time='',
        display_text='No',
    ))

    return choices, group_size


def _get_group_size_from_text(text: str) -> Tuple[str, int]:
    text = text.strip()
    size_search = re.search(r'(.*)size=(.+)', text)
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
        key='yes_{}'.format(option),
        is_yes=True,
        time=time,
        display_text='Yes ({})'.format(time),
    )


def get_time_from_raw_option(raw_option: str) -> str:
    hour = int(raw_option[:-2])
    minute = int(raw_option[-2:])

    try:
        datetime(2018, 1, 1, hour, minute)
    except ValueError:
        raise InvalidPollOption(raw_option)

    return '{}:{}'.format(hour, str(minute).zfill(2))
