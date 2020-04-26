from datetime import datetime, timedelta
import logging
from typing import List

from lunch_buddies.models.teams import Team
from lunch_buddies.models.polls import Poll
from lunch_buddies.lib.service_context import ServiceContext
from lunch_buddies.clients.stripe import LineItem, Customer


logger = logging.getLogger(__name__)


def invoice(service_context: ServiceContext) -> None:
    # find all teams with a stripe_customer_id that are signed up for invoicing
    teams = _find_teams_eligible_for_invoicing(service_context)
    for team in teams:
        if not team.stripe_customer_id:
            raise Exception('types')
        polls = _get_polls_needing_invoice(service_context, team)
        yes_users = _get_unique_yes_users_from_polls(service_context, polls)
        latest_invoice = service_context.clients.stripe.latest_invoice_for_customer(team.stripe_customer_id)

        invoice = service_context.clients.stripe.create_invoice(
            Customer(
                id=team.stripe_customer_id,
            ),
            [
                LineItem(
                    amount=10.0,
                    description='{} people responded Yes to a Lunch Buddies poll since {}'.format(
                        len(yes_users),
                        latest_invoice.created_at.strftime('%Y-%m-%d') if latest_invoice else team.created_at.strftime('%Y-%m-%d'),
                    ),
                ),
            ],
        )

        if invoice:
            for poll in polls:
                service_context.daos.polls.mark_poll_invoiced(poll, invoice.id)

    return None


def _find_teams_eligible_for_invoicing(service_context: ServiceContext) -> List[Team]:
    temp = datetime(datetime.now().year, datetime.now().month, 1) - timedelta(days=45)
    at_least_two_full_months_ago = datetime(temp.year, temp.month, 1)

    return [
        team
        for team in service_context.daos.teams.read('team_id', 'T0NPTQTA5')
        if team.stripe_customer_id and
        team.created_at > at_least_two_full_months_ago and
        team.invoicing_enabled
    ]


def _get_polls_needing_invoice(service_context: ServiceContext, team: Team) -> List[Poll]:
    return [
        poll
        for poll in service_context.daos.polls.read('team_id', team.team_id)
        if poll.state == 'CLOSED' and
        not poll.stripe_invoice_id and
        poll.created_at > (team.created_at + timedelta(days=60))
    ]


def _get_unique_yes_users_from_polls(service_context: ServiceContext, polls: List[Poll]) -> List[str]:
    return list(set([
        response.user_id
        for poll in polls
        for response in service_context.daos.poll_responses.read('callback_id', str(poll.callback_id))
        if 'yes' in response.response
    ]))
