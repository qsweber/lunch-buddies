from collections import defaultdict

from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.polls import PollsDao

poll_responses_dao = PollResponsesDao()
polls_dao = PollsDao()
polls = polls_dao.read()


polls_by_team = defaultdict(list)

for poll in polls:
    polls_by_team[poll.team_id].append(poll)

{k: len(v) for k, v in polls_by_team.items()}

agg = {k: {
    'count': len(v),
    'earliest': min(v, key=lambda x: x.created_at).created_at,
    'latest': max(v, key=lambda x: x.created_at).created_at,
} for k, v in polls_by_team.items()}

sorted(agg.items(), key=lambda v: v[1]['latest'])

{
    poll.created_at: len(poll_responses_dao.read('callback_id', str(poll.callback_id)))
    for poll in polls_by_team['T03PGMUHK']
}
