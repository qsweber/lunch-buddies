from typing import NamedTuple

from lunch_buddies.clients.dynamo import DynamoClient
from lunch_buddies.clients.http import HttpClient
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.stripe import StripeClient
from lunch_buddies.clients.sqs_v2 import SqsClient

from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.team_settings import TeamSettingsDao
from lunch_buddies.dao.groups import GroupsDao
from lunch_buddies.dao.base import Dao
from lunch_buddies.models.groups import Group


class Daos(NamedTuple):
    groups: Dao[Group]
    polls: PollsDao
    poll_responses: PollResponsesDao
    teams: TeamsDao
    team_settings: TeamSettingsDao


class Clients(NamedTuple):
    slack: SlackClient
    stripe: StripeClient
    sqs_v2: SqsClient
    http: HttpClient


class ServiceContext(NamedTuple):
    daos: Daos
    clients: Clients


dynamo = DynamoClient()


service_context = ServiceContext(
    daos=Daos(
        groups=GroupsDao(dynamo),
        polls=PollsDao(dynamo),
        poll_responses=PollResponsesDao(dynamo),
        teams=TeamsDao(dynamo),
        team_settings=TeamSettingsDao(dynamo),
    ),
    clients=Clients(
        slack=SlackClient(),
        stripe=StripeClient(),
        sqs_v2=SqsClient(),
        http=HttpClient(),
    ),
)
