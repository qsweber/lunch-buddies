from datetime import datetime
from uuid import UUID

import pytz
import pytest

from lunch_buddies.actions import create_poll as create_poll_module
from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
from lunch_buddies.models.polls import Choice
import lunch_buddies.actions.create_poll as module
from lunch_buddies.types import PollsToStartMessage, UsersToPollMessage


def test_create_poll(mocker):
    polls_dao = PollsDao()
    mocker.patch.object(
        polls_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'team_id': '123',
                'created_at': datetime.now().timestamp(),
                'channel_id': 'test_channel_id',
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': polls_constants.CLOSED,
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': polls_constants.DEFAULT_GROUP_SIZE,
            },
        ]
    )
    mocked_polls_dao_create_internal = mocker.patch.object(
        polls_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )

    expected_uuid = UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb')
    mocker.patch.object(
        create_poll_module,
        '_get_uuid',
        auto_spec=True,
        return_value=expected_uuid,
    )

    d_naive = datetime(2018, 1, 16, 7, 53, 4, 234873)
    timezone = pytz.timezone("America/Los_Angeles")
    d_aware = timezone.localize(d_naive)

    mocker.patch.object(
        create_poll_module,
        '_get_created_at',
        auto_spec=True,
        return_value=d_aware,
    )

    slack_client = SlackClient()

    mocker.patch.object(
        slack_client,
        '_channels_list_internal',
        auto_spec=True,
        return_value={'channels': [
            {'name': 'lunch_buddies', 'id': 'slack_channel_id'},
            {'name': 'foo', 'id': 'foo'},
        ]}
    )

    mocker.patch.object(
        slack_client,
        '_channels_info_internal',
        auto_spec=True,
        return_value={'channel': {'members': ['user_id_one', 'user_id_two']}}
    )

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': datetime.now().timestamp(),
        }]
    )

    result = module.create_poll(
        PollsToStartMessage(
            team_id='123',
            channel_id='test_channel_id',
            user_id='abc',
            text='',
        ),
        slack_client,
        polls_dao,
        teams_dao,
    )

    expected_poll = {
        'team_id': '123',
        'created_at': 1516117984.234873,
        'channel_id': 'test_channel_id',
        'created_by_user_id': 'abc',
        'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
        'state': polls_constants.CREATED,
        'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
        'group_size': polls_constants.DEFAULT_GROUP_SIZE,
    }

    mocked_polls_dao_create_internal.assert_called_with(
        expected_poll,
    )

    assert result == [
        UsersToPollMessage(
            team_id='123',
            user_id='user_id_one',
            callback_id=expected_uuid,
        ),
        UsersToPollMessage(
            team_id='123',
            user_id='user_id_two',
            callback_id=expected_uuid,
        )
    ]


def test_create_poll_custom_times(mocker):
    polls_dao = PollsDao()
    mocker.patch.object(
        polls_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[]
    )
    mocked_polls_dao_create_internal = mocker.patch.object(
        polls_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )

    expected_uuid = UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb')
    mocker.patch.object(
        create_poll_module,
        '_get_uuid',
        auto_spec=True,
        return_value=expected_uuid,
    )

    d_naive = datetime(2018, 1, 16, 7, 53, 4, 234873)
    timezone = pytz.timezone("America/Los_Angeles")
    d_aware = timezone.localize(d_naive)

    mocker.patch.object(
        create_poll_module,
        '_get_created_at',
        auto_spec=True,
        return_value=d_aware,
    )

    slack_client = SlackClient()

    mocker.patch.object(
        slack_client,
        '_channels_list_internal',
        auto_spec=True,
        return_value={'channels': [
            {'name': 'lunch_buddies', 'id': 'slack_channel_id'},
            {'name': 'foo', 'id': 'foo'},
        ]}
    )

    mocker.patch.object(
        slack_client,
        '_channels_info_internal',
        auto_spec=True,
        return_value={'channel': {'members': ['user_id_one', 'user_id_two']}}
    )

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': datetime.now().timestamp(),
        }]
    )

    result = module.create_poll(
        PollsToStartMessage(
            team_id='123',
            channel_id='test_channel_id',
            user_id='abc',
            text='1213',
        ),
        slack_client,
        polls_dao,
        teams_dao,
    )

    expected_poll = {
        'team_id': '123',
        'created_at': 1516117984.234873,
        'channel_id': 'test_channel_id',
        'created_by_user_id': 'abc',
        'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
        'state': polls_constants.CREATED,
        'choices': '[{"key": "yes_1213", "is_yes": true, "time": "12:13", "display_text": "Yes (12:13)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
        'group_size': polls_constants.DEFAULT_GROUP_SIZE,
    }

    mocked_polls_dao_create_internal.assert_called_with(
        expected_poll,
    )

    assert result == [
        UsersToPollMessage(
            team_id='123',
            user_id='user_id_one',
            callback_id=expected_uuid,
        ),
        UsersToPollMessage(
            team_id='123',
            user_id='user_id_two',
            callback_id=expected_uuid,
        )
    ]


def test_create_poll_messages_creating_user_if_already_closed(mocker):
    polls_dao = PollsDao()
    mocker.patch.object(
        polls_dao,
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
                'group_size': polls_constants.DEFAULT_GROUP_SIZE,
            },
        ]
    )

    slack_client = SlackClient()
    mocked_slack_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

    teams_dao = TeamsDao()
    created_at = datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': created_at.timestamp(),
        }]
    )

    result = module.create_poll(
        PollsToStartMessage(
            team_id='123',
            channel_id='test_channel_id',
            user_id='abc',
            text='',
        ),
        slack_client,
        polls_dao,
        teams_dao,
    )

    mocked_slack_post_message.assert_called_with(
        team=Team(
            team_id='123',
            access_token='fake-token',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel='abc',
        as_user=True,
        text='There is already an active poll',
    )

    assert result == []


@pytest.mark.parametrize(
    'text',
    [
        ('1145, 1230'),
        ('1145,1230'),
        ('  1145,   1230 '),
    ],
)
def test_parse_message_text_two_options(text):
    actual_choices, actual_group_size = module.parse_message_text(text)

    expected = [
        Choice(
            key='yes_1145',
            is_yes=True,
            time='11:45',
            display_text='Yes (11:45)',
        ),
        Choice(
            key='yes_1230',
            is_yes=True,
            time='12:30',
            display_text='Yes (12:30)',
        ),
        Choice(
            key='no',
            is_yes=False,
            time='',
            display_text='No',
        ),
    ]

    assert actual_choices == expected


@pytest.mark.parametrize(
    'text, expected_group_size',
    [
        ('1200', polls_constants.DEFAULT_GROUP_SIZE),
        (' 1200   ', polls_constants.DEFAULT_GROUP_SIZE),
        (' 1200   size=5', 5),
        (' 1200   size=4', 4),
    ],
)
def test_parse_message_text(text, expected_group_size):
    actual_choices, actual_group_size = module.parse_message_text(text)

    expected = [
        Choice(
            key='yes_1200',
            is_yes=True,
            time='12:00',
            display_text='Yes (12:00)',
        ),
        Choice(
            key='no',
            is_yes=False,
            time='',
            display_text='No',
        ),
    ]

    assert actual_choices == expected
    assert expected_group_size == actual_group_size


@pytest.mark.parametrize(
    'text, expected_group_size',
    [
        ('1145,1200 size=3', 3),
        (' 1145, 1200      size=5', 5),
    ],
)
def test_parse_message_text_group_multiple_times(text, expected_group_size):
    actual_choices, actual_group_size = module.parse_message_text(text)

    expected = [
        Choice(
            key='yes_1145',
            is_yes=True,
            time='11:45',
            display_text='Yes (11:45)',
        ),
        Choice(
            key='yes_1200',
            is_yes=True,
            time='12:00',
            display_text='Yes (12:00)',
        ),
        Choice(
            key='no',
            is_yes=False,
            time='',
            display_text='No',
        ),
    ]

    assert actual_choices == expected
    assert expected_group_size == actual_group_size
