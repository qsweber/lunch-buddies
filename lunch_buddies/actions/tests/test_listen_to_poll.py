from uuid import UUID

from lunch_buddies.lib.service_context import service_context
from lunch_buddies.types import ListenToPoll
import lunch_buddies.actions.listen_to_poll as module


def test_listen_to_poll(mocker, mocked_polls):
    original_message = {
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
    }

    mocker.patch.object(
        service_context.daos.poll_responses,
        '_create_internal',
        autospec=True,
        return_value=True,
    )

    outgoing_message = module.listen_to_poll(
        ListenToPoll(
            original_message=original_message,
            team_id='fake_team_id',
            user_id='fake_user_id',
            choice_key='yes_1200',
            action_ts=float('1516117984.234873'),
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
        ),
        service_context.daos.polls,
        service_context.daos.poll_responses,
    )

    expected_poll_response = {
        'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
        'user_id': 'fake_user_id',
        'created_at': float('1516117984.234873'),
        'response': 'yes_1200',
    }

    service_context.daos.poll_responses._create_internal.assert_called_with(expected_poll_response)

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
