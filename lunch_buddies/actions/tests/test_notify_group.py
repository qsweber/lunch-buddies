from datetime import datetime
import random
from uuid import UUID

from lunch_buddies.constants import polls as polls_constants
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.team_settings import TeamSettingsDao
from lunch_buddies.dao.groups import GroupsDao
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
    team_settings_dao = TeamSettingsDao()
    mocker.patch.object(
        team_settings_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[]
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

    groups_dao = GroupsDao()
    mocked_groups_dao_create_internal = mocker.patch.object(
        groups_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
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
        team_settings_dao,
        groups_dao,
    )

    expected_group = {
        'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
        'user_ids': '["user_id_one", "user_id_two"]',
        'response_key': 'yes_1145',
    }

    mocked_groups_dao_create_internal.assert_called_with(
        expected_group,
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
        text='Hello! This is your group for today. You all should meet somewhere at `11:45`. I am selecting <@user_id_two> to be in charge of picking the location.',
    )


def test_notify_group_feature_notify_in_channel(mocker):
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
    team_settings_dao = TeamSettingsDao()
    mocker.patch.object(
        team_settings_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'feature_notify_in_channel': 1,
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

    groups_dao = GroupsDao()
    mocked_groups_dao_create_internal = mocker.patch.object(
        groups_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )

    mocked_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value={
            'ts': 'fake_thread_ts',
        },
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
        team_settings_dao,
        groups_dao,
    )

    expected_group = {
        'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
        'user_ids': '["user_id_one", "user_id_two"]',
        'response_key': 'yes_1145',
    }

    mocked_groups_dao_create_internal.assert_called_with(
        expected_group,
    )

    assert mocked_post_message.call_count == 2

    mocked_post_message.assert_has_calls([
        mocker.call(
            team=Team(
                team_id='123',
                access_token='fake-token',
                name='fake-team-name',
                bot_access_token='fake-bot-token',
                created_at=created_at,
            ),
            channel='test_channel_id',
            as_user=True,
            text='Hey <@user_id_one>, <@user_id_two>! This is your group for today. You all should meet somewhere at `11:45`.',
        ),
        mocker.call(
            team=Team(
                team_id='123',
                access_token='fake-token',
                name='fake-team-name',
                bot_access_token='fake-bot-token',
                created_at=created_at,
            ),
            channel='test_channel_id',
            as_user=True,
            thread_ts='fake_thread_ts',
            text='<@user_id_two> should pick the location.',
        )
    ])
