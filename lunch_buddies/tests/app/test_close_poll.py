from datetime import datetime
import json
import os
from uuid import UUID

import pytest

from lunch_buddies.actions import close_poll as close_poll_module
from lunch_buddies.constants.help import CLOSE_POLL
from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.constants import queues as queues_constants
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.polls import Poll
import lunch_buddies.app as module


def test_close_poll_fails_without_verification_token():
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': '',
    }

    os.environ['VERIFICATION_TOKEN'] = 'wrong_verification_token'

    with pytest.raises(Exception) as excinfo:
        module._close_poll(request_form, '')

    assert 'you are not authorized to call this URL' == str(excinfo.value)


def test_close_poll_handles_help_request():
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': 'help',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    result = module._close_poll(request_form, '')

    assert result == {'text': CLOSE_POLL}


def test_close_poll(mocker):
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': '',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    sqs_client = SqsClient(queues_constants.QUEUES)
    mocked_send_message_internal = mocker.patch.object(
        sqs_client,
        '_send_message_internal',
        auto_spec=True,
        return_value=True,
    )

    module._close_poll(request_form, sqs_client)

    mocked_send_message_internal.assert_called_with(
        QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/polls_to_close',
        MessageBody='{"team_id": "123", "user_id": "abc"}',
    )


def test_close_poll_from_queue(mocker):
    sqs_client = SqsClient(queues_constants.QUEUES)
    mocked_receive_message_internal = mocker.patch.object(
        sqs_client,
        '_receive_message_internal',
        auto_spec=True,
    )
    mocked_receive_message_internal.side_effect = [
        {
            'Messages': [{
                'Body': '{"team_id": "123", "user_id": "abc"}',
                'ReceiptHandle': 'test receipt handle',
            }]
        },
        None,
        None,
        None,
        None,
    ]
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
    )

    created_at_one = datetime.now()
    created_at_two = datetime.now()

    polls_dao = PollsDao()
    mocker.patch.object(
        polls_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'team_id': '123',
                'created_at': created_at_one.timestamp(),
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': polls_constants.CREATED,
                'choices': json.dumps(polls_constants.CHOICES),
            },
            {
                'team_id': '123',
                'created_at': created_at_two.timestamp(),
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'state': polls_constants.CREATED,
                'choices': json.dumps(polls_constants.CHOICES),
            },
        ]
    )
    mocked_polls_dao_mark_poll_closed = mocker.patch.object(
        polls_dao,
        'mark_poll_closed',
        auto_spec=True,
        return_value=True,
    )

    poll_responses_dao = PollResponsesDao()
    mocker.patch.object(
        poll_responses_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'user_id': 'user_id_one',
                'created_at': float('1516117983.234873'),
                'response': 'yes_1145',
            },
            {
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'user_id': 'user_id_two',
                'created_at': float('1516117984.234873'),
                'response': 'yes_1145',
            }
        ]
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

    module._read_from_queue(
        queues_constants.POLLS_TO_CLOSE,
        close_poll_module.close_poll,
        sqs_client,
        None,
        polls_dao,
        poll_responses_dao,
        teams_dao,
    )

    mocked_polls_dao_mark_poll_closed.assert_called_with(
        poll=Poll(
            team_id='123',
            created_at=created_at_two,
            created_by_user_id='foo',
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
            state='CREATED',
            choices={'yes_1145': 'Yes (11:45)', 'yes_1230': 'Yes (12:30)', 'no': 'No'},
        ),
    )

    assert mocked_send_message_internal.call_count == 1

    mocked_send_message_internal.assert_called_with(
        MessageBody='{"team_id": "123", "response": "yes_1145", "user_ids": ["user_id_one", "user_id_two"]}',
        QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/groups_to_notify',
    )
