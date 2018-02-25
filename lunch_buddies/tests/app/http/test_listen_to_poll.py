import datetime
import json
import os

import pytest

from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
import lunch_buddies.app.http as module


def test_help_fails_without_verification_token(mocker):
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': '',
    }

    os.environ['VERIFICATION_TOKEN'] = 'wrong_verification_token'

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
        module._listen_to_poll(request_form, teams_dao, '')

    assert 'you are not authorized to call this URL' == str(excinfo.value)


def test_help_fails_without_authorized_team(mocker):
    request_form = {
        'team_id': '123',
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
        module._listen_to_poll(request_form, teams_dao, '')

    assert 'your team is not authorized for this app' == str(excinfo.value)


def test_listen_to_poll(mocker):
    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    request_payload = {
        'type': 'interactive_message',
        'actions': [{
            'name': 'answer',
            'type': 'button',
            'value': 'yes_1200'
        }],
        'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
        'team': {
            'id': 'fake_team_id',
        },
        'channel': {
            'id': 'fake_channel_id',
            'name': 'directmessage'
        },
        'user': {
            'id': 'fake_user_id',
            'name': 'quinnsweber'
        },
        'action_ts': '1516117984.234873',
        'message_ts': '1516117976.000223',
        'attachment_id': '1',
        'token': 'fake_verification_token',
        'is_app_unfurl': False,
        'original_message': {
            'text': 'Are you able to participate in Lunch Buddies today?',
            'username': 'Lunch Buddies',
            'bot_id': 'fake_bot_id',
            'attachments': [{
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'fallback': 'Something has gone wrong.',
                'id': 1,
                'color': '3AA3E3',
                'actions': [{
                    'id': '1',
                    'name': 'answer',
                    'text': 'Yes (12:00)',
                    'type': 'button',
                    'value': 'yes_1200',
                    'style': '',
                }, {
                    'id': '2',
                    'name': 'answer',
                    'text': 'No',
                    'type': 'button',
                    'value': 'no',
                    'style': '',
                }]
            }],
            'type': 'message',
            'subtype': 'bot_message',
            'ts': '1516117976.000223',
        },
        'response_url': 'fake_response_url',
        'trigger_id': 'fake_trigger_id',
    }

    polls_dao = PollsDao()

    mocker.patch.object(
        polls_dao,
        '_read_internal',
        autospec=True,
        return_value=[{
            'team_id': '123',
            'created_at': datetime.datetime.now().timestamp(),
            'created_by_user_id': 'foo',
            'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
            'state': polls_constants.CREATED,
            'choices': json.dumps(polls_constants.CHOICES),
        }],
    )

    poll_responses_dao = PollResponsesDao()

    mocked_poll_responses_dao_create = mocker.patch.object(
        poll_responses_dao,
        '_create_internal',
        autospec=True,
        return_value=True,
    )

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': 'fake_team_id',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': datetime.datetime.now().timestamp(),
        }]
    )

    outgoing_message = module._listen_to_poll(request_payload, teams_dao, polls_dao, poll_responses_dao)

    expected_poll_response = {
        'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
        'user_id': 'fake_user_id',
        'created_at': float('1516117984.234873'),
        'response': 'yes_1200',
    }

    mocked_poll_responses_dao_create.assert_called_with(expected_poll_response)

    expected_outgoing_message = {
        'text': 'Are you able to participate in Lunch Buddies today?',
        'username': 'Lunch Buddies',
        'bot_id': 'fake_bot_id',
        'attachments': [
            {
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'fallback': 'Something has gone wrong.',
                'id': 1,
                'color': '3AA3E3',
                'actions': [{
                    'id': '1',
                    'name': 'answer',
                    'text': 'Yes (12:00)',
                    'type': 'button',
                    'value': 'yes_1200',
                    'style': '',
                }, {
                    'id': '2',
                    'name': 'answer',
                    'text': 'No',
                    'type': 'button',
                    'value': 'no',
                    'style': '',
                }],
            }, {
                'text': ':white_check_mark: Your answer of `Yes (12:00)` was received!',
            },
        ],
        'type': 'message',
        'subtype': 'bot_message',
        'ts': '1516117976.000223',
    }

    assert outgoing_message == expected_outgoing_message
