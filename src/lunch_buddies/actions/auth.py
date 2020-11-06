from datetime import datetime
import json
import logging
import os

from lunch_buddies.models.teams import Team
from lunch_buddies.lib.service_context import ServiceContext
from lunch_buddies.types import Auth


logger = logging.getLogger(__name__)


def auth(
    request_form: Auth,
    service_context: ServiceContext,
) -> None:
    response = json.loads(
        service_context.clients.http.get(
            url="https://slack.com/oauth/v2/authorize",
            params={
                "client_id": os.environ["CLIENT_ID"],
                "client_secret": os.environ["CLIENT_SECRET"],
                "code": request_form.code,
            },
        ).text
    )

    logger.info("Auth response: {}".format(json.dumps(response)))

    existing_team = service_context.daos.teams.read_one("team_id", response["team_id"])

    bot_access_token = (
        existing_team.bot_access_token
        if existing_team
        else response["bot"]["bot_access_token"]
    )

    user_name, user_email = service_context.clients.slack.get_user_name_email(
        bot_access_token=bot_access_token, user_id=response["user_id"]
    )

    stripe_customer_id = None
    if not existing_team or not existing_team.stripe_customer_id:
        customer = service_context.clients.stripe.create_customer(
            name=user_name, email=user_email, team_name=response["team_name"]
        )
        if customer:
            stripe_customer_id = customer.id
    else:
        service_context.clients.stripe.update_customer(
            customer_id=existing_team.stripe_customer_id,
            name=user_name,
            email=user_email,
            team_name=response["team_name"],
        )
        stripe_customer_id = existing_team.stripe_customer_id

    if existing_team:
        team = Team(
            team_id=existing_team.team_id,
            access_token=response["access_token"],
            bot_access_token=response["bot"]["bot_access_token"],
            name=response["team_name"],
            created_at=existing_team.created_at,
            feature_notify_in_channel=existing_team.feature_notify_in_channel,
            stripe_customer_id=stripe_customer_id,
            invoicing_enabled=existing_team.invoicing_enabled,
        )
        service_context.daos.teams.update(existing_team, team)
    else:
        team = Team(
            team_id=response["team_id"],
            access_token=response["access_token"],
            bot_access_token=response["bot"]["bot_access_token"],
            name=response["team_name"],
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
        bot_access_token=bot_access_token,
        channel=response["user_id"],
        as_user=True,
        text=message,
    )

    return


def _get_created_at() -> datetime:
    return datetime.now()
