from datetime import datetime
import random
from uuid import UUID
import typing

import pytest
from pytest_mock import MockerFixture

from lunch_buddies.clients.slack import Channel
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.models.polls import Choice
from lunch_buddies.models.poll_responses import PollResponse
import lunch_buddies.actions.close_poll as module
from lunch_buddies.types import PollsToCloseMessage, GroupsToNotifyMessage
from tests.fixtures import team, poll


def test_close_poll(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_polls: MockerFixture,
    mocked_poll_responses: MockerFixture,
) -> None:
    result = module.close_poll(
        PollsToCloseMessage(
            team_id="123",
            channel_id="test_channel_id",
            user_id="abc",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    service_context.daos.polls.mark_poll_closed.assert_called_with(  # type: ignore
        poll=poll,
    )

    assert result == [
        GroupsToNotifyMessage(
            team_id="123",
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            response="yes_1130",
            user_ids=["user_id_one", "user_id_two"],
        )
    ]


def test_close_poll_null_channel(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_polls: MockerFixture,
    mocked_poll_responses: MockerFixture,
    mocked_slack: MockerFixture,
) -> None:
    result = module.close_poll(
        PollsToCloseMessage(
            team_id="123",
            channel_id="",
            user_id="abc",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    service_context.daos.polls.mark_poll_closed.assert_called_with(  # type: ignore
        poll=poll,
    )

    assert result == [
        GroupsToNotifyMessage(
            team_id="123",
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            response="yes_1130",
            user_ids=["user_id_one", "user_id_two"],
        )
    ]


def test_close_poll_null_channel_no_default_channel(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_polls: MockerFixture,
    mocked_poll_responses: MockerFixture,
) -> None:
    mocker.patch.object(
        service_context.clients.slack,
        "_channels_list_internal",
        auto_spec=True,
        return_value=[
            Channel(name="not_lunch_buddies", channel_id="test_channel_id"),
            Channel(name="foo", channel_id="foo"),
        ],
    )

    result = module.close_poll(
        PollsToCloseMessage(
            team_id="123",
            channel_id="",
            user_id="abc",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    service_context.daos.polls.mark_poll_closed.assert_called_with(  # type: ignore
        poll=poll,
    )

    assert result == [
        GroupsToNotifyMessage(
            team_id="123",
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            response="yes_1130",
            user_ids=["user_id_one", "user_id_two"],
        )
    ]


def test_close_poll_messages_creating_user_if_already_closed(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_slack: MockerFixture,
) -> None:
    poll_one = poll._replace(callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0bbb"))
    poll_two = poll._replace(state="CLOSED")
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[poll_one, poll_two],
    )

    result = module.close_poll(
        PollsToCloseMessage(
            team_id="123",
            channel_id="test_channel_id",
            user_id="closing_user_id",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    service_context.clients.slack.post_message_if_channel_exists.assert_called_with(  # type: ignore
        bot_access_token=team.bot_access_token,
        channel="closing_user_id",
        as_user=True,
        text="The poll you tried to close has already been closed",
    )

    assert result == []


def test_close_poll_messages_creating_user_if_no_responses(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_polls: MockerFixture,
    mocked_slack: MockerFixture,
) -> None:
    mocker.patch.object(
        service_context.daos.poll_responses,
        "read",
        auto_spec=True,
        return_value=[],
    )

    result = module.close_poll(
        PollsToCloseMessage(
            team_id="123",
            channel_id="test_channel_id",
            user_id="closing_user_id",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    service_context.clients.slack.post_message_if_channel_exists.assert_called_with(  # type: ignore
        bot_access_token=team.bot_access_token,
        channel="closing_user_id",
        as_user=True,
        text="No poll responses found",
    )

    service_context.daos.polls.mark_poll_closed.assert_called_with(  # type: ignore
        poll=poll,
    )

    assert result == []


def test_close_poll_messages_creating_user_if_does_not_exist(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_polls: MockerFixture,
    mocked_slack: MockerFixture,
) -> None:
    result = module.close_poll(
        PollsToCloseMessage(
            team_id="123",
            channel_id="wrong_channel_id",
            user_id="closing_user_id",
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    service_context.clients.slack.post_message_if_channel_exists.assert_called_with(  # type: ignore
        bot_access_token=team.bot_access_token,
        channel="closing_user_id",
        as_user=True,
        text="No poll found",
    )

    assert result == []


@pytest.mark.parametrize(
    "elements, group_size, min_group_size, max_group_size, expected",
    [
        (list(range(11)), 5, 3, 7, [[8, 9, 1, 2, 5, 6], [3, 7, 4, 0, 10]]),
        (
            list(range(14)),
            5,
            3,
            7,
            [[1, 10, 9, 5, 11], [2, 3, 7, 8, 4], [0, 12, 6, 13]],
        ),
        ([1], 10, 8, 10, [[1]]),
        ([1, 2], 2, 2, 2, [[1, 2]]),
        (list(range(10)), 7, 5, 7, [[7, 0, 9, 3, 2], [5, 6, 8, 1, 4]]),
        (
            list(range(18)),
            12,
            12,
            15,
            [[17, 11, 10, 13, 0, 3, 4, 5, 9], [1, 15, 8, 14, 2, 12, 16, 7, 6]],
        ),
        (
            list(range(70)),
            6,
            5,
            7,
            [
                [28, 61, 67, 42, 29, 40, 49],
                [36, 56, 52, 31, 43, 3, 53],
                [26, 54, 11, 24, 7, 10, 5],
                [15, 23, 66, 12, 2, 0, 33],
                [17, 25, 1, 63, 47, 46],
                [14, 44, 55, 20, 27, 57],
                [41, 35, 64, 21, 4, 69],
                [59, 9, 38, 45, 34, 16],
                [39, 6, 48, 60, 18, 8],
                [32, 13, 37, 22, 30, 19],
                [68, 50, 58, 51, 62, 65],
            ],
        ),
        (list(range(7)), 5, 4, 7, [[4, 2, 1, 0, 5, 6, 3]]),
        (list(range(5)), 3, 3, 7, [[2, 1, 0, 3, 4]]),
    ],
)
def test_get_groups(
    elements: typing.List[int],
    group_size: int,
    min_group_size: int,
    max_group_size: int,
    expected: typing.List[typing.List[int]],
) -> None:
    random.seed(0)

    actual = module._get_groups(elements, group_size, min_group_size, max_group_size)

    assert actual == expected


def test_get_groups_large_input() -> None:
    elements = list(range(973))

    actual = module._get_groups(elements, 10, 10, 10)

    assert len(actual) == 108
    assert max(map(len, actual)) == 10
    assert min(map(len, actual)) == 9


@pytest.mark.parametrize("elements", [(list(range(i))) for i in range(401)])
def test_get_groups_works_for_all_company_sizes(
    elements: typing.List[typing.List[int]],
) -> None:
    actual = module._get_groups(elements, 6, 5, 7)

    assert len(actual) >= 1
    assert max(map(len, actual)) <= 7


def test_group_by_answer() -> None:
    choice_1145 = Choice(
        key="yes_1145",
        is_yes=True,
        time="11:45",
        display_text="Yes (11:45)",
    )

    choice_1230 = Choice(
        key="yes_1230",
        is_yes=True,
        time="12:30",
        display_text="Yes (12:30)",
    )

    updated_poll = poll._replace(
        choices=[
            choice_1145,
            choice_1230,
            Choice(
                key="no",
                is_yes=False,
                time="",
                display_text="No",
            ),
        ]
    )

    poll_responses = [
        PollResponse(
            callback_id=UUID("450c4b9d-267b-431e-97b9-e3cb32d233c4"),
            user_id="U3LTPT61J",
            created_at=datetime(2018, 1, 31, 16, 43, 19, 93329),
            response="yes_1230",
        ),
        PollResponse(
            callback_id=UUID("450c4b9d-267b-431e-97b9-e3cb32d233c4"),
            user_id="U69J2B8E8",
            created_at=datetime(2018, 1, 31, 16, 43, 5, 494358),
            response="yes_1145",
        ),
        PollResponse(
            callback_id=UUID("450c4b9d-267b-431e-97b9-e3cb32d233c4"),
            user_id="U71ECE86R",
            created_at=datetime(2018, 1, 31, 16, 43, 26, 9092),
            response="no",
        ),
        PollResponse(
            callback_id=UUID("450c4b9d-267b-431e-97b9-e3cb32d233c4"),
            user_id="U799LRKSA",
            created_at=datetime(2018, 1, 31, 16, 43, 36, 221596),
            response="yes_1145",
        ),
    ]

    expected = {
        choice_1145: [
            PollResponse(
                callback_id=UUID("450c4b9d-267b-431e-97b9-e3cb32d233c4"),
                user_id="U69J2B8E8",
                created_at=datetime(2018, 1, 31, 16, 43, 5, 494358),
                response="yes_1145",
            ),
            PollResponse(
                callback_id=UUID("450c4b9d-267b-431e-97b9-e3cb32d233c4"),
                user_id="U799LRKSA",
                created_at=datetime(2018, 1, 31, 16, 43, 36, 221596),
                response="yes_1145",
            ),
        ],
        choice_1230: [
            PollResponse(
                callback_id=UUID("450c4b9d-267b-431e-97b9-e3cb32d233c4"),
                user_id="U3LTPT61J",
                created_at=datetime(2018, 1, 31, 16, 43, 19, 93329),
                response="yes_1230",
            ),
        ],
    }

    actual = module._group_by_answer(poll_responses, updated_poll)

    assert actual == expected
