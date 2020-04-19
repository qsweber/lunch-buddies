from datetime import datetime
import json
import logging
import os
from typing import Any

from lunch_buddies.models.teams import Team
from lunch_buddies.models.team_settings import TeamSettings
from lunch_buddies.lib.service_context import ServiceContext
from lunch_buddies.types import Auth


logger = logging.getLogger(__name__)


def auth(
    request_form: Auth,
    service_context: ServiceContext,
) -> None:
    response = json.loads(service_context.clients.http.get(
        url='https://slack.com/api/oauth.access',
        params={
            'client_id': os.environ['CLIENT_ID'],
            'client_secret': os.environ['CLIENT_SECRET'],
            'code': request_form.code,
        }
    ).text)

    logger.info('Auth response: {}'.format(json.dumps(response)))

    team = find_or_update_team(service_context, response)

    service_context.daos.team_settings.create(TeamSettings(
        team_id=team.team_id,
        feature_notify_in_channel=True,
    ))

    name, email = service_context.clients.slack.get_user_name_email(team=team, user_id=response['user_id'])

    if not team.stripe_customer_id:
        customer = service_context.clients.stripe.create_customer(name, email, team.name)
        updated_team = team._replace(stripe_customer_id=customer.id)
        service_context.daos.teams.update(team, updated_team)
    else:
        service_context.clients.stripe.update_customer(team.stripe_customer_id, name, email, team.name)

    logger.info('Installed by {} {}'.format(name, email))

    service_context.clients.slack.post_message(
        team=team,
        channel=response['user_id'],
        as_user=True,
        text='Thanks for installing Lunch Buddies! To get started, invite me to any channel and say "@Lunch Buddies create"',
    )

    return


def _get_created_at() -> datetime:
    return datetime.now()


def find_or_update_team(service_context: ServiceContext, response: Any) -> Team:
    existing_team = service_context.daos.teams.read_one('team_id', response['team_id'])

    if existing_team:
        team = Team(
            team_id=existing_team.team_id,
            access_token=response['access_token'],
            bot_access_token=response['bot']['bot_access_token'],
            name=response['team_name'],
            created_at=existing_team.created_at,
            feature_notify_in_channel=existing_team.feature_notify_in_channel,
            stripe_customer_id=existing_team.stripe_customer_id,
        )
        service_context.daos.teams.update(existing_team, team)

        return team

    team = Team(
        team_id=response['team_id'],
        access_token=response['access_token'],
        bot_access_token=response['bot']['bot_access_token'],
        name=response['team_name'],
        created_at=_get_created_at(),
        feature_notify_in_channel=True,
        stripe_customer_id=None,
    )

    service_context.daos.teams.create(team)

    return team
