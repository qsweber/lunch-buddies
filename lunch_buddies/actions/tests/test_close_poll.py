from datetime import datetime
import random
from uuid import UUID

import pytest

from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.models.polls import Choice, Poll
from lunch_buddies.models.poll_responses import PollResponse
import lunch_buddies.actions.close_poll as module
from lunch_buddies.types import PollsToCloseMessage, GroupsToNotifyMessage
from lunch_buddies.actions.tests.fixtures import team


@pytest.fixture
def mocked_polls(mocker):
    mocker.patch.object(
        service_context.daos.polls,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'team_id': '123',
                'created_at': float(1586645982.850783),
                'channel_id': 'test_channel_id',
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': polls_constants.CREATED,
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': polls_constants.DEFAULT_GROUP_SIZE,
            },
            {
                'team_id': '123',
                'created_at': float(1586645992.227006),
                'channel_id': 'test_channel_id',
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'state': polls_constants.CREATED,
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': polls_constants.DEFAULT_GROUP_SIZE,
            },
        ]
    )
    mocker.patch.object(
        service_context.daos.polls,
        'mark_poll_closed',
        auto_spec=True,
        return_value=True,
    )


@pytest.fixture
def mocked_poll_responses(mocker):
    mocker.patch.object(
        service_context.daos.poll_responses,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'user_id': 'user_id_one',
                'created_at': float('1516117983.234873'),
                'response': 'yes_1200',
            },
            {
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'user_id': 'user_id_two',
                'created_at': float('1516117984.234873'),
                'response': 'yes_1200',
            }
        ]
    )


def test_close_poll(mocker, mocked_team, mocked_polls, mocked_poll_responses):
    result = module.close_poll(
        PollsToCloseMessage(
            team_id='123',
            channel_id='test_channel_id',
            user_id='abc',
        ),
        None,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    service_context.daos.polls.mark_poll_closed.assert_called_with(
        poll=Poll(
            team_id='123',
            created_at=datetime.fromtimestamp(1586645992.227006),
            channel_id='test_channel_id',
            created_by_user_id='foo',
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
            state='CREATED',
            choices=polls_constants.CHOICES,
            group_size=polls_constants.DEFAULT_GROUP_SIZE,
        ),
    )

    assert result == [
        GroupsToNotifyMessage(
            team_id="123",
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
            response="yes_1200",
            user_ids=["user_id_one", "user_id_two"],
        )
    ]


def test_close_poll_null_channel(mocker, mocked_team, mocked_polls, mocked_poll_responses):
    mocker.patch.object(
        service_context.clients.slack,
        '_channels_list_internal',
        auto_spec=True,
        return_value=[
            {'name': 'lunch_buddies', 'id': 'test_channel_id'},
            {'name': 'foo', 'id': 'foo'},
        ]
    )

    result = module.close_poll(
        PollsToCloseMessage(
            team_id='123',
            channel_id='',
            user_id='abc',
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    service_context.daos.polls.mark_poll_closed.assert_called_with(
        poll=Poll(
            team_id='123',
            created_at=datetime.fromtimestamp(1586645992.227006),
            channel_id='test_channel_id',
            created_by_user_id='foo',
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
            state='CREATED',
            choices=polls_constants.CHOICES,
            group_size=polls_constants.DEFAULT_GROUP_SIZE,
        ),
    )

    assert result == [
        GroupsToNotifyMessage(
            team_id="123",
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
            response="yes_1200",
            user_ids=["user_id_one", "user_id_two"],
        )
    ]


def test_close_poll_null_channel_no_default_channel(mocker, mocked_team, mocked_polls, mocked_poll_responses):
    mocker.patch.object(
        service_context.clients.slack,
        '_channels_list_internal',
        auto_spec=True,
        return_value=[
            {'name': 'not_lunch_buddies', 'id': 'test_channel_id'},
            {'name': 'foo', 'id': 'foo'},
        ]
    )

    result = module.close_poll(
        PollsToCloseMessage(
            team_id='123',
            channel_id='',
            user_id='abc',
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    service_context.daos.polls.mark_poll_closed.assert_called_with(
        poll=Poll(
            team_id='123',
            created_at=datetime.fromtimestamp(1586645992.227006),
            channel_id='test_channel_id',
            created_by_user_id='foo',
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
            state='CREATED',
            choices=polls_constants.CHOICES,
            group_size=polls_constants.DEFAULT_GROUP_SIZE,
        ),
    )

    assert result == [
        GroupsToNotifyMessage(
            team_id="123",
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
            response="yes_1200",
            user_ids=["user_id_one", "user_id_two"],
        )
    ]


def test_close_poll_messages_creating_user_if_already_closed(mocker, mocked_team, mocked_slack):
    mocker.patch.object(
        service_context.daos.polls,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'team_id': '123',
                'created_at': datetime.now().timestamp(),
                'channel_id': 'test_channel_id',
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': polls_constants.CREATED,
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': 6,
            },
            {
                'team_id': '123',
                'created_at': datetime.now().timestamp(),
                'channel_id': 'test_channel_id',
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'state': polls_constants.CLOSED,
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': 6,
            },
        ]
    )

    result = module.close_poll(
        PollsToCloseMessage(
            team_id='123',
            channel_id='test_channel_id',
            user_id='closing_user_id',
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        None,
        service_context.daos.teams,
    )

    service_context.clients.slack.post_message.assert_called_with(
        bot_access_token=team.bot_access_token,
        channel='closing_user_id',
        as_user=True,
        text='The poll you tried to close has already been closed',
    )

    assert result == []


def test_close_poll_messages_creating_user_if_does_not_exist(mocker, mocked_team, mocked_polls, mocked_slack):
    result = module.close_poll(
        PollsToCloseMessage(
            team_id='123',
            channel_id='wrong_channel_id',
            user_id='closing_user_id',
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        None,
        service_context.daos.teams,
    )

    service_context.clients.slack.post_message.assert_called_with(
        bot_access_token=team.bot_access_token,
        channel='closing_user_id',
        as_user=True,
        text='No poll found',
    )

    assert result == []


@pytest.mark.parametrize(
    'elements, group_size, min_group_size, max_group_size, expected',
    [
        (list(range(11)), 5, 3, 7, [[8, 9, 1, 2, 5, 6], [3, 7, 4, 0, 10]]),
        (list(range(14)), 5, 3, 7, [[1, 10, 9, 5, 11], [2, 3, 7, 8, 4], [0, 12, 6, 13]]),
        ([1], 10, 8, 10, [[1]]),
        ([1, 2], 2, 2, 2, [[1, 2]]),
        (list(range(10)), 7, 5, 7, [[7, 0, 9, 3, 2], [5, 6, 8, 1, 4]]),
        (list(range(18)), 12, 12, 15, [[17, 11, 10, 13, 0, 3, 4, 5, 9], [1, 15, 8, 14, 2, 12, 16, 7, 6]]),
        (list(range(70)), 6, 5, 7, [
            [28, 61, 67, 42, 29, 40, 49], [36, 56, 52, 31, 43, 3, 53],
            [26, 54, 11, 24, 7, 10, 5], [15, 23, 66, 12, 2, 0, 33],
            [17, 25, 1, 63, 47, 46], [14, 44, 55, 20, 27, 57],
            [41, 35, 64, 21, 4, 69], [59, 9, 38, 45, 34, 16],
            [39, 6, 48, 60, 18, 8], [32, 13, 37, 22, 30, 19],
            [68, 50, 58, 51, 62, 65],
        ]),
        (list(range(7)), 5, 4, 7, [[4, 2, 1, 0, 5, 6, 3]]),
    ]
)
def test_get_groups(elements, group_size, min_group_size, max_group_size, expected):
    random.seed(0)

    actual = module._get_groups(elements, group_size, min_group_size, max_group_size)

    assert actual == expected


def test_get_groups_large_input():
    elements = list(range(973))

    actual = module._get_groups(elements, 10, 10, 10)

    assert len(actual) == 108
    assert max(map(len, actual)) == 10
    assert min(map(len, actual)) == 9


@pytest.mark.parametrize(
    'elements',
    [
        (list(range(i)))
        for i in range(401)
    ]
)
def test_get_groups_works_for_all_company_sizes(elements):
    actual = module._get_groups(elements, 6, 5, 7)

    assert len(actual) >= 1
    assert max(map(len, actual)) <= 7


def test_group_by_answer():
    choice_1145 = Choice(
        key='yes_1145',
        is_yes=True,
        time='11:45',
        display_text='Yes (11:45)',
    )

    choice_1230 = Choice(
        key='yes_1230',
        is_yes=True,
        time='12:30',
        display_text='Yes (12:30)',
    )

    poll = Poll(
        team_id='123',
        created_at=datetime.now(),
        channel_id='test_channel_id',
        created_by_user_id='456',
        callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'),
        state='CREATED',
        choices=[
            choice_1145,
            choice_1230,
            Choice(
                key='no',
                is_yes=False,
                time='',
                display_text='No',
            ),
        ],
        group_size=polls_constants.DEFAULT_GROUP_SIZE,
    )

    poll_responses = [
        PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U3LTPT61J', created_at=datetime(2018, 1, 31, 16, 43, 19, 93329), response='yes_1230'),
        PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U69J2B8E8', created_at=datetime(2018, 1, 31, 16, 43, 5, 494358), response='yes_1145'),
        PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U71ECE86R', created_at=datetime(2018, 1, 31, 16, 43, 26, 9092), response='no'),
        PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U799LRKSA', created_at=datetime(2018, 1, 31, 16, 43, 36, 221596), response='yes_1145'),
    ]

    expected = {
        choice_1145: [
            PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U69J2B8E8', created_at=datetime(2018, 1, 31, 16, 43, 5, 494358), response='yes_1145'),
            PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U799LRKSA', created_at=datetime(2018, 1, 31, 16, 43, 36, 221596), response='yes_1145'),
        ],
        choice_1230: [
            PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U3LTPT61J', created_at=datetime(2018, 1, 31, 16, 43, 19, 93329), response='yes_1230'),
        ],
    }

    actual = module._group_by_answer(poll_responses, poll)

    assert actual == expected
