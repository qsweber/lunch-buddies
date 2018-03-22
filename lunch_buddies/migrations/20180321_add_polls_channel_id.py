from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.clients.slack import SlackClient


def migrate():
    polls_dao = PollsDao()
    teams_dao = TeamsDao()
    slack_client = SlackClient()
    raw_polls = polls_dao._read_internal(None, None)
    dynamo_table = polls_dao._get_dynamo_table()

    for raw_poll in raw_polls:
        if 'channel_id' in raw_poll:
            continue

        team_id = raw_poll['team_id']
        team = teams_dao.read('team_id', team_id)[0]

        channel = slack_client.get_channel(team, 'lunch_buddies')

        dynamo_table.update_item(
            Key={
                'team_id': team_id,
                'created_at': raw_poll['created_at'],
            },
            AttributeUpdates={
                'channel_id': {
                    'Value': channel['id'],
                    'Action': 'PUT',
                }
            }
        )
