from typing import NamedTuple

from lunch_buddies.clients.http import HttpClient
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.stripe import StripeClient
from lunch_buddies.clients.sqs_v2 import SqsClient

from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.groups import GroupsDao


class Daos(NamedTuple):
    groups: GroupsDao
    polls: PollsDao
    poll_responses: PollResponsesDao
    teams: TeamsDao


class Clients(NamedTuple):
    slack: SlackClient
    stripe: StripeClient
    sqs_v2: SqsClient
    http: HttpClient


class ServiceContext(NamedTuple):
    daos: Daos
    clients: Clients


service_context = ServiceContext(
    daos=Daos(
        groups=GroupsDao(),
        polls=PollsDao(),
        poll_responses=PollResponsesDao(),
        teams=TeamsDao(),
    ),
    clients=Clients(
        slack=SlackClient(),
        stripe=StripeClient(),
        sqs_v2=SqsClient(),
        http=HttpClient(),
    ),
)
