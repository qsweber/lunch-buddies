from datetime import datetime
from decimal import Decimal
import json
import os

import lunch_buddies.actions.auth as module
from lunch_buddies.clients.http import HttpClient
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.team_settings import TeamSettingsDao
from lunch_buddies.models.teams import Team
from lunch_buddies.types import Auth


OATH_RESPONSE = {
    'ok': True,
    'access_token': 'xxxx-1234',
    'scope': 'identify,bot,commands,channels:write,chat:write:bot',
    'user_id': 'fake_user_id',
    'team_name': 'Fake Team Name',
    'team_id': 'fake_team_id',
    'bot': {
        'bot_user_id': 'U8PRM6XHN',
        'bot_access_token': 'xxxx-5678'
    }
}


def test_auth(mocker):
    teams_dao = TeamsDao()
    mocked_teams_dao_create_internal = mocker.patch.object(
        teams_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
    team_settings_dao = TeamSettingsDao()
    mocked_team_settings_dao_create_internal = mocker.patch.object(
        team_settings_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
    http_client = HttpClient()
    mocked_http_get = mocker.patch.object(
        http_client,
        'get',
        auto_spec=True,
        return_value=mocker.Mock(text=json.dumps(OATH_RESPONSE)),
    )
    slack_client = SlackClient()
    mocked_slack_client_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

    created_at = datetime.now()
    mocker.patch.object(
        module,
        '_get_created_at',
        auto_spec=True,
        return_value=created_at,
    )
    expected_team = Team(
        team_id='fake_team_id',
        access_token='xxxx-1234',
        bot_access_token='xxxx-5678',
        name='Fake Team Name',
        created_at=created_at
    )

    os.environ['CLIENT_ID'] = 'test_client_id'
    os.environ['CLIENT_SECRET'] = 'test_client_secret'

    module.auth(
        Auth(code='test_code'),
        teams_dao,
        team_settings_dao,
        slack_client,
        http_client,
    )

    mocked_teams_dao_create_internal.assert_called_with(
        {
            'team_id': 'fake_team_id',
            'access_token': 'xxxx-1234',
            'name': 'Fake Team Name',
            'bot_access_token': 'xxxx-5678',
            'created_at': Decimal(created_at.timestamp()),
        },
    )
    mocked_team_settings_dao_create_internal.assert_called_with(
        {
            'team_id': 'fake_team_id',
            'feature_notify_in_channel': 1,
        },
    )
    mocked_slack_client_post_message.assert_called_with(
        team=expected_team,
        channel='fake_user_id',
        as_user=True,
        text='Thanks for installing Lunch Buddies! To get started, invite me to any channel and say "@Lunch Buddies create"',
    )
    mocked_http_get.assert_called_with(
        url='https://slack.com/api/oauth.access',
        params={'client_id': 'test_client_id', 'client_secret': 'test_client_secret', 'code': 'test_code'},
    )
