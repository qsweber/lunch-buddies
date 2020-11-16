from datetime import datetime, timedelta
from uuid import UUID

import pytz
import pytest

from lunch_buddies.actions import create_poll as create_poll_module
from lunch_buddies.clients.slack import Channel
from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.models.polls import Choice
import lunch_buddies.actions.create_poll as module
from lunch_buddies.types import PollsToStartMessage, UsersToPollMessage
from tests.fixtures import team, dynamo_poll


EXPECTED_UUID = UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb")


@pytest.fixture
def mocked_module(mocker):
    mocker.patch.object(
        create_poll_module,
        "_get_uuid",
        auto_spec=True,
        return_value=EXPECTED_UUID,
    )

    d_naive = datetime(2018, 1, 16, 7, 53, 4, 234873)
    timezone = pytz.timezone("America/Los_Angeles")
    d_aware = timezone.localize(d_naive)

    mocker.patch.object(
        create_poll_module,
        "_get_created_at",
        auto_spec=True,
        return_value=d_aware,
    )


def test_create_poll(mocker, mocked_team, mocked_module, mocked_slack, mocked_polls):
    first_poll = dynamo_poll.copy()
    first_poll["state"] = "CLOSED"

    mocker.patch.object(
        service_context.daos.polls,
        "_read_internal",
        auto_spec=True,
        return_value=[first_poll],
    )

    result = module.create_poll(
        PollsToStartMessage(
            team_id="123",
            channel_id="test_channel_id",
            user_id="456",
            text="",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )

    expcted_poll = dynamo_poll.copy()
    expcted_poll[
        "choices"
    ] = '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]'
    expcted_poll["callback_id"] = str(EXPECTED_UUID)
    expcted_poll["created_at"] = 1516117984.234873
    service_context.daos.polls._create_internal.assert_called_with(expcted_poll)

    assert result == [
        UsersToPollMessage(
            team_id="123",
            user_id="user_id_one",
            callback_id=EXPECTED_UUID,
        ),
        UsersToPollMessage(
            team_id="123",
            user_id="user_id_two",
            callback_id=EXPECTED_UUID,
        ),
    ]


def test_create_poll_custom_times(
    mocker, mocked_team, mocked_module, mocked_slack, mocked_polls
):
    first_poll = dynamo_poll.copy()
    first_poll["state"] = "CLOSED"

    mocker.patch.object(
        service_context.daos.polls,
        "_read_internal",
        auto_spec=True,
        return_value=[first_poll],
    )

    result = module.create_poll(
        PollsToStartMessage(
            team_id="123",
            channel_id="test_channel_id",
            user_id="456",
            text="1213",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )

    expcted_poll = dynamo_poll.copy()
    expcted_poll["callback_id"] = str(EXPECTED_UUID)
    expcted_poll["created_at"] = 1516117984.234873
    expcted_poll[
        "choices"
    ] = '[{"key": "yes_1213", "is_yes": true, "time": "12:13", "display_text": "Yes (12:13)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]'
    service_context.daos.polls._create_internal.assert_called_with(expcted_poll)

    assert result == [
        UsersToPollMessage(
            team_id="123",
            user_id="user_id_one",
            callback_id=EXPECTED_UUID,
        ),
        UsersToPollMessage(
            team_id="123",
            user_id="user_id_two",
            callback_id=EXPECTED_UUID,
        ),
    ]


def test_create_poll_messages_creating_user_if_already_created(
    mocker, mocked_team, mocked_slack, mocked_polls
):
    first_poll = dynamo_poll.copy()
    first_poll["created_at"] = datetime.now().timestamp()

    mocker.patch.object(
        service_context.daos.polls,
        "_read_internal",
        auto_spec=True,
        return_value=[first_poll],
    )

    result = module.create_poll(
        PollsToStartMessage(
            team_id="123",
            channel_id="test_channel_id",
            user_id="456",
            text="",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )

    service_context.clients.slack.post_message.assert_called_with(
        bot_access_token=team.bot_access_token,
        channel="456",
        as_user=True,
        text="There is already an active poll",
    )

    assert result == []


def test_create_poll_works_if_existing_is_old(
    mocker, mocked_team, mocked_module, mocked_slack, mocked_polls
):
    first_poll = dynamo_poll.copy()
    first_poll["created_at"] = (datetime.now() - timedelta(days=2)).timestamp()

    mocker.patch.object(
        service_context.daos.polls,
        "_read_internal",
        auto_spec=True,
        return_value=[first_poll],
    )

    result = module.create_poll(
        PollsToStartMessage(
            team_id="123",
            channel_id="test_channel_id",
            user_id="456",
            text="",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )

    expcted_poll = dynamo_poll.copy()
    expcted_poll[
        "choices"
    ] = '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]'
    expcted_poll["callback_id"] = str(EXPECTED_UUID)
    expcted_poll["created_at"] = 1516117984.234873
    service_context.daos.polls._create_internal.assert_called_with(expcted_poll)

    assert result == [
        UsersToPollMessage(
            team_id="123",
            user_id="user_id_one",
            callback_id=EXPECTED_UUID,
        ),
        UsersToPollMessage(
            team_id="123",
            user_id="user_id_two",
            callback_id=EXPECTED_UUID,
        ),
    ]


def test_create_poll_messages_creating_user_if_default_channel_not_found(
    mocker, mocked_slack, mocked_team
):
    mocker.patch.object(
        service_context.daos.polls, "_read_internal", auto_spec=True, return_value=[]
    )

    mocker.patch.object(
        service_context.clients.slack,
        "_channels_list_internal",
        auto_spec=True,
        return_value=[
            Channel(name="not_lunch_buddies", channel_id="test_channel_id"),
            Channel(name="foo", channel_id="foo"),
        ],
    )

    result = module.create_poll(
        PollsToStartMessage(
            team_id="123",
            channel_id="",
            user_id="456",
            text="",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )

    service_context.clients.slack.post_message.assert_called_with(
        bot_access_token=team.bot_access_token,
        channel="456",
        as_user=True,
        text=module.DEFAULT_CHANNEL_NOT_FOUND,
    )

    assert result == []


def test_create_poll_messages_creating_user_if_not_member_of_default_channel(
    mocker, mocked_slack, mocked_team
):
    mocker.patch.object(
        service_context.daos.polls, "_read_internal", auto_spec=True, return_value=[]
    )

    mocker.patch.object(
        service_context.clients.slack,
        "conversations_members",
        auto_spec=True,
        return_value=["user_id_one", "user_id_two"],
    )

    result = module.create_poll(
        PollsToStartMessage(
            team_id="123",
            channel_id="",
            user_id="456",
            text="",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )

    service_context.clients.slack.post_message.assert_called_with(
        bot_access_token=team.bot_access_token,
        channel="456",
        as_user=True,
        text='Error creating poll. To create a poll via the slash command "/lunch_buddies_create", you must be a member of <#test_channel_id|lunch_buddies>. You can join that channel and try again.',
    )

    assert result == []


@pytest.mark.parametrize(
    "text",
    [("1145, 1230"), ("1145,1230"), ("  1145,   1230 ")],
)
def test_parse_message_text_two_options(text):
    actual_choices, actual_group_size = module.parse_message_text(text)

    expected = [
        Choice(
            key="yes_1145",
            is_yes=True,
            time="11:45",
            display_text="Yes (11:45)",
        ),
        Choice(
            key="yes_1230",
            is_yes=True,
            time="12:30",
            display_text="Yes (12:30)",
        ),
        Choice(
            key="no",
            is_yes=False,
            time="",
            display_text="No",
        ),
    ]

    assert actual_choices == expected


@pytest.mark.parametrize(
    "text, expected_group_size",
    [
        ("1200", polls_constants.DEFAULT_GROUP_SIZE),
        (" 1200   ", polls_constants.DEFAULT_GROUP_SIZE),
        (" 1200   size=5", 5),
        (" 1200   size=4", 4),
    ],
)
def test_parse_message_text(text, expected_group_size):
    actual_choices, actual_group_size = module.parse_message_text(text)

    expected = [
        Choice(
            key="yes_1200",
            is_yes=True,
            time="12:00",
            display_text="Yes (12:00)",
        ),
        Choice(
            key="no",
            is_yes=False,
            time="",
            display_text="No",
        ),
    ]

    assert actual_choices == expected
    assert expected_group_size == actual_group_size


@pytest.mark.parametrize(
    "text, expected_group_size",
    [("1145,1200 size=3", 3), (" 1145, 1200      size=5", 5)],
)
def test_parse_message_text_group_multiple_times(text, expected_group_size):
    actual_choices, actual_group_size = module.parse_message_text(text)

    expected = [
        Choice(
            key="yes_1145",
            is_yes=True,
            time="11:45",
            display_text="Yes (11:45)",
        ),
        Choice(
            key="yes_1200",
            is_yes=True,
            time="12:00",
            display_text="Yes (12:00)",
        ),
        Choice(
            key="no",
            is_yes=False,
            time="",
            display_text="No",
        ),
    ]

    assert actual_choices == expected
    assert expected_group_size == actual_group_size
