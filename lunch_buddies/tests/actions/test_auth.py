from datetime import datetime
import json
import os

import lunch_buddies.actions.auth as module
from lunch_buddies.clients.slack import SlackClient
import lunch_buddies.constants.slack as slack_constants
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
from lunch_buddies.tests.fixtures.dao import TEAM as team_fixture
from lunch_buddies.tests.fixtures.slack import OAUTH_RESPONSE as oath_response_fixture


def test_auth(mocker):
    teams_dao = TeamsDao()
    mocked_teams_dao_create_internal = mocker.patch.object(
        teams_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
    created_at = datetime.fromtimestamp(float(team_fixture['created_at']))
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[team_fixture]
    )

    mocker.patch.object(
        module,
        '_get_slack_oauth',
        auto_spec=True,
        return_value=mocker.Mock(text=json.dumps(oath_response_fixture)),
    )

    mocker.patch.object(
        module,
        '_get_created_at',
        auto_spec=True,
        return_value=created_at,
    )

    slack_client = SlackClient()

    mocker.patch.object(
        slack_client,
        '_channels_list_internal',
        auto_spec=True,
        return_value={'channels': []},
    )
    mocked_slack_client_create_channel = mocker.patch.object(
        slack_client,
        'create_channel',
        auto_spec=True,
        return_value=True,
    )

    module.auth(
        {'code': 'test_code'},
        teams_dao,
        slack_client,
    )

    mocked_teams_dao_create_internal.assert_called_with(
        team_fixture,
    )

    mocked_slack_client_create_channel.assert_called_with(
        team=Team(**{**team_fixture, **{'created_at': created_at}}),
        name='lunch_buddies',
        is_private=False,
    )


def test_auth_handles_case_when_channel_already_exists(mocker):
    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[team_fixture],
    )

    mocker.patch.object(
        module,
        '_get_slack_oauth',
        auto_spec=True,
        return_value=mocker.Mock(text=json.dumps(oath_response_fixture)),
    )

    slack_client = SlackClient()

    mocker.patch.object(
        slack_client,
        '_channels_list_internal',
        auto_spec=True,
        return_value={'channels': [{'name': slack_constants.LUNCH_BUDDIES_CHANNEL_NAME}]},
    )
    mocked_slack_client_create_channel = mocker.patch.object(
        slack_client,
        'create_channel',
        auto_spec=True,
        return_value=True,
    )

    module.auth(
        {'code': 'test_code'},
        teams_dao,
        slack_client,
    )

    mocked_slack_client_create_channel.assert_not_called()


def test_calls_correct_slack_endpoint(mocker):
    mocked_requests_get = mocker.patch.object(
        module.requests,
        'get',
        auto_spec=True,
    )

    os.environ['CLIENT_ID'] = 'fake_client_id'
    os.environ['CLIENT_SECRET'] = 'fake_client_secret'

    module._get_slack_oauth({'code': 'test_code'})

    mocked_requests_get.assert_called_with(
        'https://slack.com/api/oauth.access',
        params={
            'client_id': 'fake_client_id',
            'client_secret': 'fake_client_secret',
            'code': 'test_code',
        },
    )
