import datetime
from uuid import UUID

from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.types import ListenToPoll
import lunch_buddies.actions.listen_to_poll as module


def test_listen_to_poll(mocker):
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

    polls_dao = PollsDao()
    mocker.patch.object(
        polls_dao,
        '_read_internal',
        autospec=True,
        return_value=[{
            'team_id': '123',
            'created_at': datetime.datetime.now().timestamp(),
            'channel_id': 'test_channel_id',
            'created_by_user_id': 'foo',
            'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
            'state': polls_constants.CREATED,
            'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
            'group_size': polls_constants.DEFAULT_GROUP_SIZE,
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

    outgoing_message = module.listen_to_poll(
        ListenToPoll(
            original_message=original_message,
            team_id='fake_team_id',
            user_id='fake_user_id',
            choice_key='yes_1200',
            action_ts=float('1516117984.234873'),
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
        ),
        polls_dao,
        poll_responses_dao,
    )

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
