import datetime
from decimal import Decimal
import json

import lunch_buddies.actions.auth as module
from lunch_buddies.dao.teams import TeamsDao


def test_auth(mocker):
    teams_dao = TeamsDao()
    mocked_teams_dao_create_internal = mocker.patch.object(
        teams_dao,
        '_create_internal',
        auto_spec=True,
        return_value=True,
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

    created_at = datetime.datetime.now()

    mocker.patch.object(
        module,
        '_get_created_at',
        auto_spec=True,
        return_value=created_at
    )

    module.auth(
        {'code': 'test_code'},
        teams_dao,
    )

    mocked_teams_dao_create_internal.assert_called_with(
        {
            'team_id': 'XXXXXXXXXX',
            'access_token': 'xoxp-XXXXXXXX-XXXXXXXX-XXXXX',
            'bot_access_token': 'xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT',
            'created_at': Decimal(created_at.timestamp()),
        }
    )
