from collections import defaultdict

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao

poll_responses_dao = PollResponsesDao()
polls_dao = PollsDao()
polls = polls_dao.read()
slack_client = SlackClient()
teams_dao = TeamsDao()
teams = teams_dao.read()

polls_by_team = defaultdict(list)

for poll in polls:
    polls_by_team[poll.team_id].append(poll)


def team_summary(team_id, polls):
    team = teams_dao.read('team_id', team_id)[0]
    team_info = slack_client._get_base_client_for_team(team.bot_access_token).api_call('team.info')

    return {
        'name': team_info['team']['name'] if team_info['ok'] else '',
        'count': len(polls),
        'earliest': min(polls, key=lambda x: x.created_at).created_at,
        'latest': max(polls, key=lambda x: x.created_at).created_at,
    }


agg = {k: team_summary(k, v) for k, v in polls_by_team.items()}

sorted(agg.items(), key=lambda v: v[1]['latest'])

{
    poll.created_at: len(poll_responses_dao.read('callback_id', str(poll.callback_id)))
    for poll in polls_by_team['T03PGMUHK']
}
