from datetime import datetime
from decimal import Decimal
import json

import lunch_buddies.actions.auth as module
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team


def test_auth(mocker):
    teams_dao = TeamsDao()
    mocked_teams_dao_create_internal = mocker.patch.object(
        teams_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
    created_at = datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'xoxp-XXXXXXXX-XXXXXXXX-XXXXX',
            'bot_access_token': 'xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT',
            'created_at': created_at.timestamp(),
        }]
    )

    mocker.patch.object(
        module,
        '_get_slack_oauth',
        auto_spec=True,
        return_value=mocker.Mock(text=json.dumps({
            "access_token": "xoxp-XXXXXXXX-XXXXXXXX-XXXXX",
            "scope": "incoming-webhook,commands,bot",
            "team_name": "Team Installing Your Hook",
            "team_id": "XXXXXXXXXX",
            "incoming_webhook": {
                "url": "https://hooks.slack.com/TXXXXX/BXXXXX/XXXXXXXXXX",
                "channel": "#channel-it-will-post-to",
                "configuration_url": "https://teamname.slack.com/services/BXXXXX"
            },
            "bot": {
                "bot_user_id": "UTTTTTTTTTTR",
                "bot_access_token": "xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT"
            }
        })),
    )

    mocker.patch.object(
        module,
        '_get_created_at',
        auto_spec=True,
        return_value=created_at
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
        {
            'team_id': 'XXXXXXXXXX',
            'access_token': 'xoxp-XXXXXXXX-XXXXXXXX-XXXXX',
            'bot_access_token': 'xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT',
            'created_at': Decimal(created_at.timestamp()),
        }
    )

    mocked_slack_client_create_channel.assert_called_with(
        team=Team(
            team_id='123',
            access_token='xoxp-XXXXXXXX-XXXXXXXX-XXXXX',
            bot_access_token='xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT',
            created_at=created_at,
        ),
        name='lunch_buddies',
        is_private=False,
    )


def test_auth_handles_case_when_channel_already_exists(mocker):
    teams_dao = TeamsDao()
    mocked_teams_dao_create_internal = mocker.patch.object(
        teams_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
    created_at = datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'xoxp-XXXXXXXX-XXXXXXXX-XXXXX',
            'bot_access_token': 'xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT',
            'created_at': created_at.timestamp(),
        }]
    )

    mocker.patch.object(
        module,
        '_get_slack_oauth',
        auto_spec=True,
        return_value=mocker.Mock(text=json.dumps({
            "access_token": "xoxp-XXXXXXXX-XXXXXXXX-XXXXX",
            "scope": "incoming-webhook,commands,bot",
            "team_name": "Team Installing Your Hook",
            "team_id": "XXXXXXXXXX",
            "incoming_webhook": {
                "url": "https://hooks.slack.com/TXXXXX/BXXXXX/XXXXXXXXXX",
                "channel": "#channel-it-will-post-to",
                "configuration_url": "https://teamname.slack.com/services/BXXXXX"
            },
            "bot": {
                "bot_user_id": "UTTTTTTTTTTR",
                "bot_access_token": "xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT"
            }
        })),
    )

    mocker.patch.object(
        module,
        '_get_created_at',
        auto_spec=True,
        return_value=created_at
    )

    slack_client = SlackClient()

    mocker.patch.object(
        slack_client,
        '_channels_list_internal',
        auto_spec=True,
        return_value={'channels': [{'name': 'lunch_buddies'}]},
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
        {
            'team_id': 'XXXXXXXXXX',
            'access_token': 'xoxp-XXXXXXXX-XXXXXXXX-XXXXX',
            'bot_access_token': 'xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT',
            'created_at': Decimal(created_at.timestamp()),
        }
    )

    mocked_slack_client_create_channel.assert_not_called()
