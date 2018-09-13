from datetime import datetime
from uuid import UUID

from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
import lunch_buddies.actions.poll_user as module
from lunch_buddies.types import UsersToPollMessage


def test_poll_user(mocker):
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
            'group_size': polls_constants.DEFAULT_GROUP_SIZE,
        }]
    )

    module.poll_user(
        UsersToPollMessage(
            team_id='123',
            user_id='test_user_id',
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
        ),
        slack_client,
        polls_dao,
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
