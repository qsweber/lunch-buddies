from collections import defaultdict

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao

poll_responses_dao = PollResponsesDao()
polls_dao = PollsDao()
polls = polls_dao.read()
teams_dao = TeamsDao()
teams = teams_dao.read()
slack_client = SlackClient()

polls_by_team: dict = defaultdict(list)

for poll in polls:
    polls_by_team[poll.team_id].append(poll)


def team_summary(team_id, polls):
    team = teams_dao.read('team_id', team_id)[0]

    return {
        'name': team.name,
        'count': len(polls),
        'earliest': min(polls, key=lambda x: x.created_at).created_at,
        'latest': max(polls, key=lambda x: x.created_at).created_at,
        'foo': max(polls, key=lambda x: x.created_at),
        'error': slack_client._get_base_client_for_team(team.bot_access_token).api_call('auth.test').get('error')
    }


agg = {k: team_summary(k, v) for k, v in polls_by_team.items()}

sorted(agg.items(), key=lambda v: v[1]['latest'])

{
    v['name']: v['error']
    for k, v in agg.items()
}
