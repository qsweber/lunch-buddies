from collections import defaultdict
import typing

from lunch_buddies.models.polls import Poll
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao


def run() -> None:
    polls_dao = PollsDao()
    polls = polls_dao.read(None, None)
    teams_dao = TeamsDao()
    teams = teams_dao.read(None, None)

    polls_by_team: typing.Dict[str, typing.List[Poll]] = defaultdict(list)

    for poll in polls:
        polls_by_team[poll.team_id].append(poll)

    team = [t for t in teams if t.name == "foo"][0]

    polls = polls_by_team[team.team_id]
    polls.sort(key=lambda p: p.created_at)
    # bad_poll = polls[-1]

    for poll in polls:
        if poll.state == "CREATED":
            print("closing {}".format(poll))
            polls_dao.mark_poll_closed(poll)
