import datetime
import os

import pytest

from lunch_buddies.constants.help import CREATE_POLL
from lunch_buddies.constants import queues as queues_constants
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.dao.teams import TeamsDao
import lunch_buddies.app.http as module


def test_create_poll_fails_without_verification_token(mocker):
    request_form = {
        'team_id': '123',
        'channel_id': 'test_channel_id',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': '',
    }

    os.environ['VERIFICATION_TOKEN'] = 'wrong_verification_token'
    os.environ['VERIFICATION_TOKEN_DEV'] = 'wrong_dev_verification_token'

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': datetime.datetime.now().timestamp(),
        }]
    )

    with pytest.raises(Exception) as excinfo:
        module._create_poll(request_form, teams_dao, '')

    assert 'you are not authorized to call this URL' == str(excinfo.value)


def test_create_poll_fails_without_authorized_team(mocker):
    request_form = {
        'team_id': '123',
        'channel_id': 'test_channel_id',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': '',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[]
    )

    with pytest.raises(Exception) as excinfo:
        module._create_poll(request_form, teams_dao, '')

    assert 'your team is not authorized for this app' == str(excinfo.value)


def test_create_poll_handles_help_request(mocker):
    request_form = {
        'team_id': '123',
        'channel_id': 'test_channel_id',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': 'help',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': datetime.datetime.now().timestamp(),
        }]
    )

    result = module._create_poll(request_form, teams_dao, '')

    assert result == {'text': CREATE_POLL}


def test_create_poll_fails_with_bad_text(mocker):
    sqs_client = SqsClient(queues_constants.QUEUES)

    request_form = {
        'team_id': '123',
        'channel_id': 'test_channel_id',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': 'foo bar',  # this is bad
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': datetime.datetime.now().timestamp(),
        }]
    )

    result = module._create_poll(request_form, teams_dao, sqs_client)

    assert result == {'text': 'Failed: Option could not be parsed into a time: "foo bar"'}


def test_create_poll(mocker):
    sqs_client = SqsClient(queues_constants.QUEUES)

    request_form = {
        'team_id': '123',
        'channel_id': 'test_channel_id',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': '1200, 1230',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    mocked_send_message_internal = mocker.patch.object(
        sqs_client,
        '_send_message_internal',
        auto_spec=True,
        return_value=True,
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
            'created_at': datetime.datetime.now().timestamp(),
        }]
    )

    module._create_poll(request_form, teams_dao, sqs_client)

    mocked_send_message_internal.assert_called_with(
        QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/polls_to_start',
        MessageBody='{"team_id": "123", "channel_id": "test_channel_id", "user_id": "abc", "text": "1200, 1230"}',
    )


def test_create_poll_null_channel_id(mocker):
    sqs_client = SqsClient(queues_constants.QUEUES)

    request_form = {
        'team_id': '123',
        'channel_id': None,
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': '1200, 1230',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    mocked_send_message_internal = mocker.patch.object(
        sqs_client,
        '_send_message_internal',
        auto_spec=True,
        return_value=True,
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
            'created_at': datetime.datetime.now().timestamp(),
        }]
    )

    module._create_poll(request_form, teams_dao, sqs_client)

    mocked_send_message_internal.assert_called_with(
        QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/polls_to_start',
        MessageBody='{"team_id": "123", "channel_id": null, "user_id": "abc", "text": "1200, 1230"}',
    )
