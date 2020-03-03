from typing import NamedTuple

from lunch_buddies.clients.http import HttpClient
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sns import SnsClient
from lunch_buddies.clients.sqs import SqsClient

from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.team_settings import TeamSettingsDao
from lunch_buddies.dao.groups import GroupsDao


class Daos(NamedTuple):
    groups: GroupsDao
    polls: PollsDao
    poll_responses: PollResponsesDao
    teams: TeamsDao
    team_settings: TeamSettingsDao


class Clients(NamedTuple):
    slack: SlackClient
    sqs: SqsClient
    sns: SnsClient
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
        team_settings=TeamSettingsDao(),
    ),
    clients=Clients(
        slack=SlackClient(),
        sns=SnsClient(),
        sqs=SqsClient(),
        http=HttpClient(),
    ),
)
