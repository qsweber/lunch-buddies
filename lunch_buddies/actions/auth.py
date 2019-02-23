from datetime import datetime
import json
import logging
import os

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.http import HttpClient
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.team_settings import TeamSettingsDao
from lunch_buddies.models.teams import Team
from lunch_buddies.models.team_settings import TeamSettings
from lunch_buddies.types import Auth


logger = logging.getLogger(__name__)


def auth(
    request_form: Auth,
    teams_dao: TeamsDao,
    team_settings_dao: TeamSettingsDao,
    slack_client: SlackClient,
    http_client: HttpClient,
) -> None:
    response = json.loads(http_client.get(
        url='https://slack.com/api/oauth.access',
        params={
            'client_id': os.environ['CLIENT_ID'],
            'client_secret': os.environ['CLIENT_SECRET'],
            'code': request_form.code,
        }
    ).text)

    team = Team(
        team_id=response['team_id'],
        access_token=response['access_token'],
        bot_access_token=response['bot']['bot_access_token'],
        name=response['team_name'],
        created_at=_get_created_at(),
    )

    teams_dao.create(team)

    team_settings_dao.create(TeamSettings(
        team_id=team.team_id,
        feature_notify_in_channel=True,
    ))

    slack_client.post_message(
        team=team,
        channel=response['user_id'],
        as_user=True,
        text='Thanks for installing Lunch Buddies! To get started, invite me to any channel and say "@Lunch Buddies create"',
    )

    return


def _get_created_at() -> datetime:
    return datetime.now()
