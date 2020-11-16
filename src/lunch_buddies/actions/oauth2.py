from datetime import datetime
import json
import logging
import os

from lunch_buddies.models.teams import Team
from lunch_buddies.lib.service_context import ServiceContext
from lunch_buddies.types import Auth


logger = logging.getLogger(__name__)


def oauth2(
    request_form: Auth,
    service_context: ServiceContext,
) -> None:
    # While Slack is confirming my new oauth flow, need to prioritize using the dev token
    client_id = (
        os.environ["CLIENT_ID_DEV"]
        if "CLIENT_ID_DEV" in os.environ
        else os.environ["CLIENT_ID"]
    )
    client_secret = (
        os.environ["CLIENT_SECRET_DEV"]
        if "CLIENT_SECRET_DEV" in os.environ
        else os.environ["CLIENT_SECRET"]
    )

    response = json.loads(
        service_context.clients.http.get(
            url="https://slack.com/api/oauth.v2.access",
            params={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": request_form.code,
            },
        ).text
    )

    logger.info("Auth response: {}".format(json.dumps(response)))

    team_id = response["team"]["id"]
    existing_team = service_context.daos.teams.read_one("team_id", team_id)

    new_bot_access_token = response["access_token"]
    team_name = response["team"]["name"]
    user_id = response["authed_user"]["id"]

    user = service_context.clients.slack.get_user_info(
        bot_access_token=(
            # TODO: not sure why I did it this way
            existing_team.bot_access_token
            if existing_team
            else new_bot_access_token
        ),
        user_id=user_id,
    )
    user_name = user.name
    user_email = user.email

    stripe_customer_id = None
    if not existing_team or not existing_team.stripe_customer_id:
        customer = service_context.clients.stripe.create_customer(
            name=user_name, email=user_email, team_name=team_name
        )
        if customer:
            stripe_customer_id = customer.id
    else:
        service_context.clients.stripe.update_customer(
            customer_id=existing_team.stripe_customer_id,
            name=user_name,
            email=user_email,
            team_name=team_name,
        )
        stripe_customer_id = existing_team.stripe_customer_id

    if existing_team:
        team = Team(
            team_id=existing_team.team_id,
            access_token="DEPRECATED",
            bot_access_token=new_bot_access_token,
            name=team_name,
            created_at=existing_team.created_at,
            feature_notify_in_channel=existing_team.feature_notify_in_channel,
            stripe_customer_id=stripe_customer_id,
            invoicing_enabled=existing_team.invoicing_enabled,
        )
        service_context.daos.teams.update(existing_team, team)
    else:
        team = Team(
            team_id=team_id,
            access_token="DEPRECATED",
            bot_access_token=new_bot_access_token,
            name=team_name,
            created_at=_get_created_at(),
            feature_notify_in_channel=True,
            stripe_customer_id=stripe_customer_id,
            invoicing_enabled=True,
        )
        service_context.daos.teams.create(team)

    logger.info("Installed by {} {}".format(user_name, user_email))

    message = "Thanks for installing Lunch Buddies! To get started, invite me to any channel and say `@Lunch Buddies create`."

    if team.invoicing_enabled:
        message += "\n\nFor information about pricing, check out https://www.lunchbuddiesapp.com/pricing/"

    service_context.clients.slack.post_message(
        bot_access_token=new_bot_access_token,
        channel=user_id,
        as_user=True,
        text=message,
    )

    return


def _get_created_at() -> datetime:
    return datetime.now()
