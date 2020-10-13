from datetime import datetime, timedelta
import logging
import re
from typing import List
import pytz

from lunch_buddies.dao.groups import GroupsDao
from lunch_buddies.models.polls import Poll, Choice
from lunch_buddies.models.teams import Team
from lunch_buddies.types import BotMention
from lunch_buddies.lib.service_context import ServiceContext


logger = logging.getLogger(__name__)


def get_summary(
    message: BotMention,
    rest_of_command: str,
    team: Team,
    service_context: ServiceContext,
) -> str:
    polls = service_context.daos.polls.read("team_id", team.team_id)

    if not polls:
        return ""

    lookback_days = _get_lookback_days(rest_of_command)

    polls_filtered = [
        poll
        for poll in polls
        if poll.created_at > (datetime.now() - timedelta(days=lookback_days))
    ]

    user_tz = service_context.clients.slack.get_user_tz(
        team.bot_access_token, message.user_id
    )

    return "\n\n".join(
        [
            _get_summary_for_poll(poll, service_context.daos.groups, user_tz)
            for poll in polls_filtered
        ]
    )


def _get_lookback_days(rest_of_command: str) -> int:
    search = re.search(r"([0-9]+)", rest_of_command)

    return int(search.groups("0")[0]) if search else 7


def _get_summary_for_poll(poll: Poll, groups_dao: GroupsDao, user_tz: str) -> str:
    created_at = (
        datetime.utcfromtimestamp(poll.created_at.timestamp())
        .replace(tzinfo=pytz.timezone("UTC"))
        .astimezone(pytz.timezone(user_tz))
        .strftime("%B %d, %Y")
    )

    header = "*{}: started by* <@{}>".format(
        created_at,
        poll.created_by_user_id,
    )

    groups = groups_dao.read("callback_id", str(poll.callback_id))

    if not groups:
        raise Exception("groups not found")

    # TODO: order the groups

    summary = "\n".join(
        [
            "{}: {}".format(
                _get_choice_from_key(group.response_key, poll.choices).display_text,
                " ".join(["<@{}>".format(user_id) for user_id in group.user_ids]),
            )
            for group in groups
        ]
    )

    return "{}\n{}".format(header, summary)


def _get_choice_from_key(key: str, choices: List[Choice]) -> Choice:
    return [choice for choice in choices if choice.key == key][0]
