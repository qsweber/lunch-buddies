import datetime
import json

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants import polls as polls_constants, queues as queues_constants
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
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
                'choices': json.dumps(polls_constants.CHOICES),
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
        queues_constants.PollsToStartMessage(team_id='123', user_id='creating_user_id'),
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
        queues_constants.PollsToStartMessage(team_id='123', user_id='creating_user_id'),
        slack_client,
        sqs_client,
        polls_dao,
        None,
        teams_dao,
    )

    assert mocked_slack_post_message.not_called()

    assert mocked_send_message_internal.call_count == 2
