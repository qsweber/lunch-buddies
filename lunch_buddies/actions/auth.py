import datetime
import json
import os

import requests

from lunch_buddies.clients.slack import ChannelDoesNotExist
from lunch_buddies.constants.slack import LUNCH_BUDDIES_CHANNEL_NAME
from lunch_buddies.models.teams import Team


def auth(request_args, teams_dao, slack_client):
    response = _get_slack_oauth(request_args)

    response_dict = json.loads(response.text)

    teams_dao.create(Team(
        team_id=response_dict['team_id'],
        access_token=response_dict['access_token'],
        bot_access_token=response_dict['bot']['bot_access_token'],
        created_at=_get_created_at(),
    ))

    team = teams_dao.read('team_id', response_dict['team_id'])[0]

    try:
        slack_client.get_channel(team=team, name=LUNCH_BUDDIES_CHANNEL_NAME)
    except ChannelDoesNotExist:
        print(slack_client.create_channel(team=team, name=LUNCH_BUDDIES_CHANNEL_NAME, is_private=False))

    return True


def _get_slack_oauth(request_args):
    return requests.get('https://slack.com/api/oauth.access', params={
        'client_id': os.environ['CLIENT_ID'],
        'client_secret': os.environ['CLIENT_SECRET'],
        'code': request_args['code'],
    })


def _get_created_at():
    return datetime.datetime.now()
