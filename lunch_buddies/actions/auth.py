import datetime
import json
import logging
import os

import requests

from lunch_buddies.clients.slack import ChannelDoesNotExist
from lunch_buddies.constants.slack import LUNCH_BUDDIES_CHANNEL_NAME
from lunch_buddies.models.teams import Team


logger = logging.getLogger(__name__)


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
        slack_client.create_channel(team=team, name=LUNCH_BUDDIES_CHANNEL_NAME, is_private=False)

    return True


def _get_slack_oauth(request_args):
    request_client_id = request_args['client_id']

    production_client_id = os.environ['CLIENT_ID']
    development_client_id = os.environ['CLIENT_ID_DEV']

    if request_client_id == production_client_id:
        client_secret = os.environ['CLIENT_SECRET']
    elif request_client_id == development_client_id:
        client_secret = os.environ['CLIENT_SECRET_DEV']
    else:
        raise Exception('client id does not match expectation')

    return requests.get('https://slack.com/api/oauth.access', params={
        'client_id': request_client_id,
        'client_secret': client_secret,
        'code': request_args['code'],
    })


def _get_created_at():
    return datetime.datetime.now()
