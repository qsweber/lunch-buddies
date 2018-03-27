from datetime import datetime

from lunch_buddies.actions import poll_user as poll_user_module
from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.constants import queues as queues_constants
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
import lunch_buddies.app.handlers as module


def test_poll_users_from_queue(mocker):
    sqs_client = SqsClient(queues_constants.QUEUES)

    mocked_receive_message_internal = mocker.patch.object(
        sqs_client,
        '_receive_message_internal',
        auto_spec=True,
    )
    mocked_receive_message_internal.side_effect = [
        {
            'Messages': [{
                'Body': '{"team_id": "123", "user_id": "test_user_id", "callback_id": {"_type": "UUID", "value": "f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb"}}',
                'ReceiptHandle': 'test receipt handle',
            }]
        },
        None,
        None,
        None,
        None,
    ]
    mocker.patch.object(
        sqs_client,
        '_delete_message_internal',
        auto_spec=True,
        return_value=True,
    )

    slack_client = SlackClient()

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

    mocked_slack_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

    polls_dao = PollsDao()

    mocker.patch.object(
        polls_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'created_at': datetime.now().timestamp(),
            'channel_id': 'test_channel_id',
            'created_by_user_id': 'foo',
            'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
            'state': polls_constants.CREATED,
            'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
        }]
    )

    module._read_from_queue(
        queues_constants.USERS_TO_POLL,
        poll_user_module.poll_user,
        sqs_client,
        slack_client,
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
        attachments=[{
            'fallback': 'Something has gone wrong.',
            'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
            'color': '#3AA3E3',
            'attachment_type': 'default',
            'actions': [
                {'name': 'answer', 'text': 'Yes (12:00)', 'type': 'button', 'value': 'yes_1200'},
                {'name': 'answer', 'text': 'No', 'type': 'button', 'value': 'no'},
            ]
        }],
        channel='test_user_id',
        as_user=True,
        text='Are you able to participate in Lunch Buddies today?',
    )
