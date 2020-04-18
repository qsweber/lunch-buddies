import logging

from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.clients.slack import SlackClient


logger = logging.getLogger(__name__)


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
        team = teams_dao.read_one_or_die('team_id', team_id)

        test = slack_client._channels_list_internal(team)
        if isinstance(test, dict) and 'error' in test:
            logger.error('Error with team {}: {}'.format(team_id, test['error']))
            continue

        try:
            channel = slack_client.get_channel(team, 'lunch_buddies')
        except Exception as e:
            logger.error('Error with team {}: {}'.format(team_id, str(e)))
            continue

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
