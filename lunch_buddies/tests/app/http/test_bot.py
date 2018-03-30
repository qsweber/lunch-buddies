import datetime
import os

import pytest

import lunch_buddies.app.http as module
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants.help import APP_EXPLANATION
from lunch_buddies.constants import queues as queues_constants
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
from lunch_buddies.tests.fixtures.slack import BOT_EVENT


def test_bot_fails_without_verification_token(mocker):
    request_form = BOT_EVENT.copy()
    request_form['team_id'] = 'test_team_id'
    request_form['token'] = 'wrong_verification_token'

    os.environ['VERIFICATION_TOKEN'] = 'verification_token'
    os.environ['VERIFICATION_TOKEN_DEV'] = 'dev_verification_token'

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': 'test_team_id',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': datetime.datetime.now().timestamp(),
        }]
    )

    with pytest.raises(Exception) as excinfo:
        module._bot(request_form, teams_dao, None, None, None, None)

    assert 'you are not authorized to call this URL' == str(excinfo.value)


def test_bot_fails_without_authorized_team(mocker):
    request_form = BOT_EVENT.copy()
    request_form['team_id'] = 'wrong_team_id'
    request_form['token'] = 'verification_token'

    os.environ['VERIFICATION_TOKEN'] = 'verification_token'

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[]
    )

    with pytest.raises(Exception) as excinfo:
        module._bot(request_form, teams_dao, None, None, None, None)

    assert 'your team is not authorized for this app' == str(excinfo.value)


def test_help(mocker):
    request_form = BOT_EVENT.copy()
    request_form['team_id'] = 'test_team_id'
    request_form['token'] = 'verification_token'
    request_form['event']['text'] = '<@TESTBOTID> help'

    os.environ['VERIFICATION_TOKEN'] = 'verification_token'

    teams_dao = TeamsDao()
    created_at = datetime.datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': 'test_team_id',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': created_at.timestamp(),
        }]
    )

    # sqs_client = SqsClient(queues_constants.QUEUES)
    # mocked_send_message_internal = mocker.patch.object(
    #     sqs_client,
    #     '_send_message_internal',
    #     auto_spec=True,
    #     return_value=True,
    # )

    slack_client = SlackClient()
    mocked_slack_client_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True
    )

    module._bot(request_form, teams_dao, slack_client, None, None, None)

    mocked_slack_client_post_message.assert_called_with(
        team=Team(
            team_id='test_team_id',
            access_token='fake-token',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel='test_channel_id',
        as_user=True,
        text=APP_EXPLANATION,
    )


def test_create(mocker):
    request_form = BOT_EVENT.copy()
    request_form['team_id'] = 'test_team_id'
    request_form['token'] = 'verification_token'
    request_form['event']['text'] = '<@TESTBOTID> create 1230, 1300'

    os.environ['VERIFICATION_TOKEN'] = 'verification_token'

    teams_dao = TeamsDao()
    created_at = datetime.datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': 'test_team_id',
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

    slack_client = SlackClient()
    mocked_slack_client_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True
    )

    module._bot(request_form, teams_dao, slack_client, sqs_client, None, None)

    mocked_slack_client_post_message.assert_called_with(
        team=Team(
            team_id='test_team_id',
            access_token='fake-token',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel=request_form['event']['channel'],
        as_user=True,
        text='ok!',
    )

    mocked_send_message_internal.assert_called_with(
        QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/polls_to_start',
        MessageBody='{"team_id": "test_team_id", "channel_id": "test_channel_id", "user_id": "test_user_id", "text": "1230, 1300"}',
    )


def test_close(mocker):
    request_form = BOT_EVENT.copy()
    request_form['team_id'] = 'test_team_id'
    request_form['token'] = 'verification_token'
    request_form['event']['text'] = '<@TESTBOTID> close'

    os.environ['VERIFICATION_TOKEN'] = 'verification_token'

    teams_dao = TeamsDao()
    created_at = datetime.datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': 'test_team_id',
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

    slack_client = SlackClient()
    mocked_slack_client_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True
    )

    module._bot(request_form, teams_dao, slack_client, sqs_client, None, None)

    mocked_slack_client_post_message.assert_called_with(
        team=Team(
            team_id='test_team_id',
            access_token='fake-token',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel=request_form['event']['channel'],
        as_user=True,
        text='ok!',
    )

    mocked_send_message_internal.assert_called_with(
        QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/polls_to_close',
        MessageBody='{"team_id": "test_team_id", "channel_id": "test_channel_id", "user_id": "test_user_id"}',
    )
