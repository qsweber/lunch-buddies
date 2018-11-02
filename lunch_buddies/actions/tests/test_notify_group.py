from datetime import datetime
import random
from uuid import UUID

from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
import lunch_buddies.actions.notify_group as module
from lunch_buddies.types import GroupsToNotifyMessage


def test_notify_group(mocker):
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
            'name': 'fake-team-name',
            'bot_access_token': 'fake-bot-token',
            'created_at': created_at.timestamp(),
        }]
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
                'channel_id': 'test_channel_id',
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'state': polls_constants.CREATED,
                'choices': '[{"key": "yes_1145", "is_yes": true, "time": "11:45", "display_text": "Yes (11:45)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': polls_constants.DEFAULT_GROUP_SIZE,
            },
        ]
    )
    mocker.patch.object(
        slack_client,
        'open_conversation',
        auto_spec=True,
        return_value={'channel': {'id': 'new_group_message_channel'}}
    )
    mocked_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True,
    )
    random.seed(0)

    module.notify_group(
        GroupsToNotifyMessage(
            team_id='123',
            callback_id=UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb'),
            response='yes_1145',
            user_ids=['user_id_one', 'user_id_two'],
        ),
        slack_client,
        polls_dao,
        teams_dao,
    )

    assert mocked_post_message.call_count == 1

    mocked_post_message.assert_called_with(
        team=Team(
            team_id='123',
            access_token='fake-token',
            name='fake-team-name',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel='new_group_message_channel',
        as_user=True,
        text='Hello! This is your lunch group for today. You all should meet somewhere at `11:45`. I am selecting <@user_id_two> to be in charge of picking the location.',
    )
