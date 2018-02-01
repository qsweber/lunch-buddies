from datetime import datetime
import json
import os

import pytest

from lunch_buddies.actions import close_poll as close_poll_module
from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.constants import queues as queues_constants
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
import lunch_buddies.app as module


def test_close_poll(mocker):
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
    }

    sqs_client = SqsClient(queues_constants.QUEUES)
    mocked_send_message_internal = mocker.patch.object(
        sqs_client,
        '_send_message_internal',
        auto_spec=True,
        return_value=True,
    )

    os.environ['APP_ADMIN'] = 'abc'

    module._close_poll(request_form, sqs_client)

    mocked_send_message_internal.assert_called_with(
        QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/polls_to_close',
        MessageBody='{"team_id": "123"}',
    )


def test_close_poll_fails_if_not_app_admin(mocker):
    sqs_client = SqsClient(queues_constants.QUEUES)

    request_form = {
        'team_id': '123',
        'user_id': 'not_app_admin'
    }

    os.environ['APP_ADMIN'] = 'abc'

    with pytest.raises(Exception) as excinfo:
        module._close_poll(request_form, sqs_client)

    assert 'you are not authorized to close a poll' == str(excinfo.value)


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
                'Body': '{"team_id": "123"}',
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

    polls_dao = PollsDao()
    mocker.patch.object(
        polls_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'team_id': '123',
                'created_at': datetime.now().timestamp(),
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': polls_constants.CREATED,
                'choices': json.dumps(polls_constants.CHOICES),
            },
            {
                'team_id': '123',
                'created_at': datetime.now().timestamp(),
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'state': polls_constants.CREATED,
                'choices': json.dumps(polls_constants.CHOICES),
            },
        ]
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

    module._read_from_queue(
        queues_constants.POLLS_TO_CLOSE,
        close_poll_module.close_poll,
        sqs_client,
        None,
        polls_dao,
        poll_responses_dao,
    )

    assert mocked_send_message_internal.call_count == 1

    mocked_send_message_internal.assert_called_with(
        MessageBody='{"team_id": "123", "response": "yes_1145", "user_ids": ["user_id_one", "user_id_two"]}',
        QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/groups_to_notify',
    )
