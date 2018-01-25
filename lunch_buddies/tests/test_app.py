from datetime import datetime
import os
from uuid import UUID

import pytest

from lunch_buddies.actions import create_poll as create_poll_module
from lunch_buddies.models.polls import Poll
from lunch_buddies.constants.polls import CREATED, CHOICES
from lunch_buddies.constants.queues import QUEUES, POLLS_TO_START
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
import lunch_buddies.app as module


@pytest.fixture
def sqs_client(mocker):
    client = SqsClient(QUEUES)

    mocker.patch.object(
        client,
        '_send_message_internal',
        auto_spec=True,
        return_value=True,
    )
    mocker.patch.object(
        client,
        '_receive_message_internal',
        auto_spec=True,
        return_value=True,
    )
    mocker.patch.object(
        client,
        '_delete_message_internal',
        auto_spec=True,
        return_value=True,
    )

    return client


@pytest.fixture
def slack_client(mocker):
    os.environ['SLACK_API_TOKEN'] = 'foo'
    client = SlackClient()

    mocker.patch.object(
        client,
        'list_users',
        auto_spec=True,
        return_value=[{'is_bot': False, 'name': 'test user name', 'id': 'test_user_id'}],
    )

    return client


@pytest.fixture
def polls_dao(mocker):
    dao = PollsDao()

    mocker.patch.object(
        dao,
        'create',
        auto_spec=True,
        return_value=True,
    )

    return dao


@pytest.fixture
def poll_responses_dao():
    return PollResponsesDao()


def test_create_poll(mocker, sqs_client):
    request_form = {
        'team_id': '123',
        'user_id': 'abc'
    }

    mocked_send_message_internal = mocker.patch.object(
        sqs_client,
        '_send_message_internal',
        auto_spec=True,
        return_value=True,
    )

    module._create_poll(request_form, sqs_client)

    mocked_send_message_internal.assert_called_with(
        QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/polls_to_start',
        MessageBody='{"team_id": "123", "user_id": "abc"}',
    )


def test_create_poll_from_queue_creates_poll(mocker, sqs_client, slack_client, polls_dao, poll_responses_dao):
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

    mocked_polls_dao_create = mocker.patch.object(
        polls_dao,
        'create',
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        create_poll_module,
        '_get_uuid',
        auto_spec=True,
        return_value=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb')
    )

    mocker.patch.object(
        create_poll_module,
        '_get_created_at',
        auto_spec=True,
        return_value=datetime.strptime('2018-01-10', '%Y-%m-%d'),
    )

    module._read_from_queue(
        POLLS_TO_START,
        create_poll_module.create_poll,
        sqs_client,
        slack_client,
        polls_dao,
        poll_responses_dao,
    )

    expected_poll = Poll(
        team_id='123',
        created_at=datetime.strptime('2018-01-10', '%Y-%m-%d'),
        created_by_user_id='abc',
        callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
        state=CREATED,
        choices=CHOICES,
    )

    mocked_polls_dao_create.assert_called_with(
        expected_poll,
    )


def test_create_poll_from_queue_receives_four_times(mocker, sqs_client, slack_client, polls_dao, poll_responses_dao):
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

    module._read_from_queue(
        POLLS_TO_START,
        create_poll_module.create_poll,
        sqs_client,
        slack_client,
        polls_dao,
        poll_responses_dao,
    )

    assert mocked_receive_message_internal.call_count == 4
