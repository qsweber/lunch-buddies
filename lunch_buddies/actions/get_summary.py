import logging

from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.groups import GroupsDao
from lunch_buddies.models.teams import Team
from lunch_buddies.types import BotMention


logger = logging.getLogger(__name__)


def get_summary(
    message: BotMention,
    rest_of_command: str,
    team: Team,
    polls_dao: PollsDao,
    groups_dao: GroupsDao,
) -> str:
    polls = polls_dao.read('team_id', team.team_id)

    logger.info('found {} polls for team {}'.format(len(polls), team.team_id))

    return 'found {} polls for team {}'.format(len(polls), team.team_id)
