from datetime import datetime
from uuid import UUID

import pytz

from lunch_buddies.actions import create_poll as create_poll_module
from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.constants import queues as queues_constants
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
import lunch_buddies.app.handlers as module


def test_create_poll_from_queue(mocker):
    sqs_client = SqsClient(queues_constants.QUEUES)

    mocked_receive_message_internal = mocker.patch.object(
        sqs_client,
        '_receive_message_internal',
        auto_spec=True,
    )
    mocked_receive_message_internal.side_effect = [
        {
            'Messages': [{
                'Body': '{"team_id": "123", "user_id": "abc", "text": ""}',
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
        return_value=True,
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
                'state': polls_constants.CLOSED,
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
            },
        ]
    )

    mocked_polls_dao_create_internal = mocker.patch.object(
        polls_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        create_poll_module,
        '_get_uuid',
        auto_spec=True,
        return_value=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb')
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

    mocked_slack_client_users_info_internal = mocker.patch.object(
        slack_client,
        '_users_info_internal',
        auto_spec=True,
    )
    mocked_slack_client_users_info_internal.side_effect = [
        {'user': {'id': 'user_id_one', 'name': 'user_name_one', 'is_bot': False}},
        {'user': {'id': 'user_id_two', 'name': 'user_name_two', 'is_bot': False}},
    ]

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

    module._read_from_queue(
        queues_constants.POLLS_TO_START,
        create_poll_module.create_poll,
        sqs_client,
        slack_client,
        polls_dao,
        None,
        teams_dao,
    )

    expected_poll = {
        'team_id': '123',
        'created_at': 1516117984.234873,
        'created_by_user_id': 'abc',
        'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
        'state': polls_constants.CREATED,
        'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
    }

    mocked_polls_dao_create_internal.assert_called_with(
        expected_poll,
    )

    assert mocked_receive_message_internal.call_count == 4

    mocked_send_message_internal.assert_has_calls(
        [
            mocker.call(
                MessageBody='{"team_id": "123", "user_id": "user_id_one", "callback_id": {"_type": "UUID", "value": "f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb"}}',
                QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/users_to_poll',
            ),
            mocker.call(
                MessageBody='{"team_id": "123", "user_id": "user_id_two", "callback_id": {"_type": "UUID", "value": "f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb"}}',
                QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/users_to_poll',
            ),
        ]
    )

    assert mocked_send_message_internal.call_count == 2


def test_create_poll_from_queue_custom_times(mocker):
    sqs_client = SqsClient(queues_constants.QUEUES)

    mocked_receive_message_internal = mocker.patch.object(
        sqs_client,
        '_receive_message_internal',
        auto_spec=True,
    )
    mocked_receive_message_internal.side_effect = [
        {
            'Messages': [{
                'Body': '{"team_id": "123", "user_id": "abc", "text": "1200"}',
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
        return_value=True,
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
                'state': polls_constants.CLOSED,
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
            },
        ]
    )

    mocked_polls_dao_create_internal = mocker.patch.object(
        polls_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        create_poll_module,
        '_get_uuid',
        auto_spec=True,
        return_value=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb')
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

    mocked_slack_client_users_info_internal = mocker.patch.object(
        slack_client,
        '_users_info_internal',
        auto_spec=True,
    )
    mocked_slack_client_users_info_internal.side_effect = [
        {'user': {'id': 'user_id_one', 'name': 'user_name_one', 'is_bot': False}},
        {'user': {'id': 'user_id_two', 'name': 'user_name_two', 'is_bot': False}},
    ]

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

    module._read_from_queue(
        queues_constants.POLLS_TO_START,
        create_poll_module.create_poll,
        sqs_client,
        slack_client,
        polls_dao,
        None,
        teams_dao,
    )

    expected_poll = {
        'team_id': '123',
        'created_at': 1516117984.234873,
        'created_by_user_id': 'abc',
        'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
        'state': polls_constants.CREATED,
        'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
    }

    mocked_polls_dao_create_internal.assert_called_with(
        expected_poll,
    )

    assert mocked_receive_message_internal.call_count == 4

    mocked_send_message_internal.assert_has_calls(
        [
            mocker.call(
                MessageBody='{"team_id": "123", "user_id": "user_id_one", "callback_id": {"_type": "UUID", "value": "f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb"}}',
                QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/users_to_poll',
            ),
            mocker.call(
                MessageBody='{"team_id": "123", "user_id": "user_id_two", "callback_id": {"_type": "UUID", "value": "f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb"}}',
                QueueUrl='https://us-west-2.queue.amazonaws.com/120356305272/users_to_poll',
            ),
        ]
    )

    assert mocked_send_message_internal.call_count == 2
