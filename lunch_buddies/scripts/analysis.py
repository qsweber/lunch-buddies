from collections import defaultdict

from lunch_buddies.lib.service_context import service_context


def run() -> None:
    polls = service_context.daos.polls.read(None, None)
    polls_by_team: dict = defaultdict(list)

    for poll in polls:
        polls_by_team[poll.team_id].append(poll)

    teams = service_context.daos.teams.read(None, None)

    def team_summary(team):
        polls = polls_by_team[team.team_id]
        # print(polls)
        latest_poll = None if len(polls) == 0 else max(polls, key=lambda x: x.created_at)

        return {
            'name': team.name,
            'count': 0 if len(polls) == 0 else len(polls),
            'earliest': None if len(polls) == 0 else min(polls, key=lambda x: x.created_at).created_at,
            'latest': None if not latest_poll else latest_poll.created_at,
            'latest_poll': latest_poll,
            'responses_in_latest': 0 if not latest_poll else len(service_context.daos.poll_responses.read('callback_id', str(latest_poll.callback_id))),
            # 'error': service_context.clients.slack._get_base_client_for_token(team.bot_access_token).api_call('auth.test').get('error'),
            'team': team,
        }

    agg = {team: team_summary(team) for team in teams}

    # sorted(agg.items(), key=lambda v: v[1]['count'])
    sorted(agg.items(), key=lambda v: v[1]['team'].created_at)

    {
        v['name']: v['error']
        for k, v in agg.items()
    }
