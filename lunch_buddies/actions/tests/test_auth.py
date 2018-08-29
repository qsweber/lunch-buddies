from datetime import datetime
from decimal import Decimal
import json
import os

import lunch_buddies.actions.auth as module
from lunch_buddies.clients.http import HttpClient
from lunch_buddies.clients.slack import SlackClient
import lunch_buddies.constants.slack as slack_constants
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
from lunch_buddies.types import Auth


OATH_RESPONSE = {
    "access_token": "xoxp-XXXXXXXX-XXXXXXXX-XXXXX",
    "scope": "incoming-webhook,commands,bot",
    "team_name": "Team Installing Your Hook",
    "team_id": "123",
    "incoming_webhook": {
        "url": "https://hooks.slack.com/TXXXXX/BXXXXX/XXXXXXXXXX",
        "channel": "#channel-it-will-post-to",
        "configuration_url": "https://teamname.slack.com/services/BXXXXX"
    },
    "bot": {
        "bot_user_id": "UTTTTTTTTTTR",
        "bot_access_token": "xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT"
    }
}


def _get_mocked_teams_dao(mocker):
    teams_dao = TeamsDao()
    mocked_teams_dao_create_internal = mocker.patch.object(
        teams_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[]
    )

    return teams_dao, mocked_teams_dao_create_internal


def _get_mocked_http_client(mocker):
    http_client = HttpClient()
    mocked_http_get = mocker.patch.object(
        http_client,
        'get',
        auto_spec=True,
        return_value=mocker.Mock(text=json.dumps(OATH_RESPONSE)),
    )

    return http_client, mocked_http_get


def _get_mocked_slack_client(mocker, existing_channels):
    slack_client = SlackClient()
    mocker.patch.object(
        slack_client,
        '_channels_list_internal',
        auto_spec=True,
        return_value={'channels': existing_channels},
    )
    mocked_slack_client_create_channel = mocker.patch.object(
        slack_client,
        'create_channel',
        auto_spec=True,
        return_value=True,
    )

    return slack_client, mocked_slack_client_create_channel


def test_auth(mocker):
    teams_dao, mocked_teams_dao_create_internal = _get_mocked_teams_dao(mocker)
    http_client, mocked_http_get = _get_mocked_http_client(mocker)
    slack_client, mocked_slack_client_create_channel = _get_mocked_slack_client(mocker, [])

    created_at = datetime.now()
    mocker.patch.object(
        module,
        '_get_created_at',
        auto_spec=True,
        return_value=created_at,
    )
    expected_team = Team(
        team_id='123',
        access_token='xoxp-XXXXXXXX-XXXXXXXX-XXXXX',
        bot_access_token='xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT',
        created_at=created_at
    )

    os.environ['CLIENT_ID'] = 'test_client_id'
    os.environ['CLIENT_SECRET'] = 'test_client_secret'

    module.auth(
        Auth(code='test_code'),
        teams_dao,
        slack_client,
        http_client,
    )

    mocked_teams_dao_create_internal.assert_called_with(
        {
            'team_id': '123',
            'access_token': 'xoxp-XXXXXXXX-XXXXXXXX-XXXXX',
            'bot_access_token': 'xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT',
            'created_at': Decimal(created_at.timestamp()),
        },
    )
    mocked_slack_client_create_channel.assert_called_with(
        team=expected_team,
        name='lunch_buddies',
        is_private=False,
    )
    mocked_http_get.assert_called_with(
        url='https://slack.com/api/oauth.access',
        params={'client_id': 'test_client_id', 'client_secret': 'test_client_secret', 'code': 'test_code'},
    )


def test_auth_handles_case_when_channel_already_exists(mocker):
    teams_dao, mocked_teams_dao_create_internal = _get_mocked_teams_dao(mocker)
    http_client, mocked_http_get = _get_mocked_http_client(mocker)
    slack_client, mocked_slack_client_create_channel = _get_mocked_slack_client(
        mocker,
        [{'name': slack_constants.LUNCH_BUDDIES_CHANNEL_NAME}],
    )

    module.auth(
        Auth(code='test_code'),
        teams_dao,
        slack_client,
        http_client,
    )

    mocked_slack_client_create_channel.assert_not_called()
