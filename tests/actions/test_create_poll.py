from datetime import datetime, timedelta
from uuid import UUID

import pytz
import pytest
from pytest_mock import MockerFixture

from lunch_buddies.actions import create_poll as create_poll_module
from lunch_buddies.clients.slack import Channel
from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.models.polls import Choice
import lunch_buddies.actions.create_poll as module
from lunch_buddies.types import PollsToStartMessage, UsersToPollMessage
from tests.fixtures import team, poll


EXPECTED_UUID = UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb")
d_naive = datetime(2018, 1, 16, 7, 53, 4, 234873)
timezone = pytz.timezone("America/Los_Angeles")
EXPECTED_CREATED_AT = timezone.localize(d_naive)


@pytest.fixture
def mocked_module(mocker: MockerFixture) -> None:
    mocker.patch.object(
        create_poll_module,
        "_get_uuid",
        auto_spec=True,
        return_value=EXPECTED_UUID,
    )

    mocker.patch.object(
        create_poll_module,
        "_get_created_at",
        auto_spec=True,
        return_value=EXPECTED_CREATED_AT,
    )


def test_create_poll(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_module: MockerFixture,
    mocked_slack: MockerFixture,
    mocked_polls: MockerFixture,
) -> None:
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[poll._replace(state="CLOSED")],
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

    expcted_poll = poll._replace(
        choices=polls_constants.CHOICES,
        callback_id=EXPECTED_UUID,
        created_at=EXPECTED_CREATED_AT,
    )
    service_context.daos.polls.create.assert_called_with(expcted_poll)  # type: ignore

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
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_module: MockerFixture,
    mocked_slack: MockerFixture,
    mocked_polls: MockerFixture,
) -> None:
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[poll._replace(state="CLOSED")],
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

    expcted_poll = poll._replace(
        choices=[
            Choice(
                key="yes_1213",
                is_yes=True,
                time="12:13",
                display_text="Yes (12:13)",
            ),
            Choice(
                key="no",
                is_yes=False,
                time="",
                display_text="No",
            ),
        ],
        callback_id=EXPECTED_UUID,
        created_at=EXPECTED_CREATED_AT,
    )
    service_context.daos.polls.create.assert_called_with(expcted_poll)  # type: ignore

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
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_slack: MockerFixture,
    mocked_polls: MockerFixture,
) -> None:
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[poll._replace(created_at=datetime.now())],
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

    service_context.clients.slack.post_message_if_channel_exists.assert_called_with(  # type: ignore
        bot_access_token=team.bot_access_token,
        channel="456",
        as_user=True,
        text="There is already an active poll",
    )

    assert result == []


def test_create_poll_works_if_existing_is_old(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_module: MockerFixture,
    mocked_slack: MockerFixture,
    mocked_polls: MockerFixture,
) -> None:
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[poll._replace(created_at=(datetime.now() - timedelta(days=2)))],
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

    expcted_poll = poll._replace(
        choices=polls_constants.CHOICES,
        callback_id=EXPECTED_UUID,
        created_at=EXPECTED_CREATED_AT,
    )
    service_context.daos.polls.create.assert_called_with(expcted_poll)  # type: ignore

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
    mocker: MockerFixture, mocked_slack: MockerFixture, mocked_team: MockerFixture
) -> None:
    mocker.patch.object(
        service_context.daos.polls, "read", auto_spec=True, return_value=[]
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

    service_context.clients.slack.post_message_if_channel_exists.assert_called_with(  # type: ignore
        bot_access_token=team.bot_access_token,
        channel="456",
        as_user=True,
        text=module.DEFAULT_CHANNEL_NOT_FOUND,
    )

    assert result == []


def test_create_poll_messages_creating_user_if_not_member_of_default_channel(
    mocker: MockerFixture, mocked_slack: MockerFixture, mocked_team: MockerFixture
) -> None:
    mocker.patch.object(
        service_context.daos.polls, "read", auto_spec=True, return_value=[]
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

    service_context.clients.slack.post_message_if_channel_exists.assert_called_with(  # type: ignore
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
def test_parse_message_text_two_options(text: str) -> None:
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
def test_parse_message_text(text: str, expected_group_size: int) -> None:
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
def test_parse_message_text_group_multiple_times(
    text: str, expected_group_size: int
) -> None:
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
