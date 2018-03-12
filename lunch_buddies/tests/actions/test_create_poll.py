import datetime

import pytest

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants import polls as polls_constants, queues as queues_constants
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
from lunch_buddies.models.polls import Choice, ChoiceList
import lunch_buddies.actions.create_poll as module


def test_create_poll_messages_creating_user_if_already_closed(mocker):
    polls_dao = PollsDao()
    mocker.patch.object(
        polls_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'team_id': '123',
                'created_at': datetime.datetime.now().timestamp(),
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': polls_constants.CREATED,
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
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
    created_at = datetime.datetime.now()
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

    module.create_poll(
        queues_constants.PollsToStartMessage(
            team_id='123',
            user_id='creating_user_id',
            text='',
        ),
        slack_client,
        None,
        polls_dao,
        None,
        teams_dao,
    )

    mocked_slack_post_message.assert_called_with(
        team=Team(
            team_id='123',
            access_token='fake-token',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel='creating_user_id',
        as_user=True,
        text='There is already an active poll',
    )


def test_create_poll_handles_first_time(mocker):
    polls_dao = PollsDao()
    mocker.patch.object(
        polls_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[]
    )
    mocker.patch.object(
        polls_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )

    slack_client = SlackClient()
    mocked_slack_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

    teams_dao = TeamsDao()
    created_at = datetime.datetime.now()
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

    sqs_client = SqsClient(queues_constants.QUEUES)
    mocked_send_message_internal = mocker.patch.object(
        sqs_client,
        '_send_message_internal',
        auto_spec=True,
        return_value=True,
    )
    mocker.patch.object(
        sqs_client,
        '_delete_message_internal',
        auto_spec=True,
        return_value=True,
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

    mocked_slack_client_users_info_internal = mocker.patch.object(
        slack_client,
        '_users_info_internal',
        auto_spec=True,
    )
    mocked_slack_client_users_info_internal.side_effect = [
        {'user': {'id': 'user_id_one', 'name': 'user_name_one', 'is_bot': False}},
        {'user': {'id': 'user_id_two', 'name': 'user_name_two', 'is_bot': False}},
    ]

    module.create_poll(
        queues_constants.PollsToStartMessage(
            team_id='123',
            user_id='creating_user_id',
            text='',
        ),
        slack_client,
        sqs_client,
        polls_dao,
        None,
        teams_dao,
    )

    assert mocked_slack_post_message.not_called()

    assert mocked_send_message_internal.call_count == 2


@pytest.mark.parametrize(
    'text',
    [
        ('1145, 1230'),
        ('1145,1230'),
        ('  1145,   1230 '),
    ],
)
def test_get_choices_from_message_text_two_options(text):
    actual = module.get_choices_from_message_text(text)

    expected = ChoiceList([
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
    ])

    assert actual == expected


@pytest.mark.parametrize(
    'text',
    [
        ('1200'),
        (' 1200   '),
    ],
)
def test_get_choices_from_message_text_one_option(text):
    actual = module.get_choices_from_message_text(text)

    expected = ChoiceList([
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
    ])

    assert actual == expected
