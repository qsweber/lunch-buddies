from datetime import datetime, timedelta
import logging
from typing import List
from json import dumps

from lunch_buddies.models.teams import Team
from lunch_buddies.models.polls import Poll
from lunch_buddies.lib.service_context import ServiceContext
from lunch_buddies.clients.stripe import LineItem, Customer


logger = logging.getLogger(__name__)


def invoice(service_context: ServiceContext, dry_run: bool) -> None:
    # find all teams with a stripe_customer_id that are signed up for invoicing
    teams = _find_teams_eligible_for_invoicing(service_context)
    for team in teams:
        logger.info("Starting invoicing for {} {}".format(team.team_id, team.name))
        if not team.stripe_customer_id:
            raise Exception("making mypy happy")
        polls = _get_polls_needing_invoice(service_context, team)
        line_item = _get_line_item(service_context, team, polls)

        if line_item.amount == 0:
            logger.info("No need to invoice team {}".format(team.name))
            continue

        if dry_run:
            logger.info(
                "Would invoice team {} with {}".format(
                    team.name, dumps(line_item._asdict())
                )
            )
            continue

        invoice = service_context.clients.stripe.create_invoice(
            Customer(
                id=team.stripe_customer_id,
            ),
            [line_item],
        )

        if invoice:
            for poll in polls:
                service_context.daos.polls.mark_poll_invoiced(poll, invoice.id)

    return None


def _get_line_item(
    service_context: ServiceContext, team: Team, polls: List[Poll]
) -> LineItem:
    if not team.stripe_customer_id:
        raise Exception("making mypy happy")
    yes_users = _get_unique_yes_users_from_polls(service_context, polls)
    latest_invoice = service_context.clients.stripe.latest_invoice_for_customer(
        team.stripe_customer_id
    )
    return LineItem(
        amount=len(yes_users) * 1.0,
        description="{} people responded Yes to a Lunch Buddies poll since {}".format(
            len(yes_users),
            latest_invoice.created_at.strftime("%Y-%m-%d")
            if latest_invoice
            else (team.created_at + timedelta(days=30)).strftime("%Y-%m-%d"),
        ),
    )


def _find_teams_eligible_for_invoicing(service_context: ServiceContext) -> List[Team]:
    now = _get_now()
    temp = datetime(now.year, now.month, 1) - timedelta(days=15)
    at_least_one_full_month_ago = datetime(temp.year, temp.month, 1)

    return [
        team
        for team in service_context.daos.teams.read(None, None)
        if team.stripe_customer_id
        and team.created_at < at_least_one_full_month_ago
        and team.invoicing_enabled
    ]


def _get_polls_needing_invoice(
    service_context: ServiceContext, team: Team
) -> List[Poll]:
    return [
        poll
        for poll in service_context.daos.polls.read("team_id", team.team_id)
        if poll.state == "CLOSED"
        and not poll.stripe_invoice_id
        and poll.created_at > (team.created_at + timedelta(days=30))
    ]


def _get_unique_yes_users_from_polls(
    service_context: ServiceContext, polls: List[Poll]
) -> List[str]:
    return list(
        set(
            [
                response.user_id
                for poll in polls
                for response in service_context.daos.poll_responses.read(
                    "callback_id", str(poll.callback_id)
                )
                if "yes" in response.response
            ]
        )
    )


def _get_now():
    return datetime.now()
