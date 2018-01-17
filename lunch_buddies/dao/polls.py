import datetime
from decimal import Decimal
import json

import boto3
from boto3.dynamodb.conditions import Key

from lunch_buddies.models.polls import Poll


def create(poll):
    dynamodb = boto3.resource('dynamodb')

    polls_table = dynamodb.Table('lunch_buddies_polls')

    poll_for_dynamo = {
        'team_id': poll.team_id,
        'created_at_ts': Decimal(poll.created_at_ts),
        'created_by_user_id': poll.created_by_user_id,
        'callback_id': poll.callback_id,
        'state': poll.state,
        'created_at': datetime.datetime.now().isoformat(),
        'raw': json.dumps(poll.raw),
    }

    polls_table.put_item(
        Item=poll_for_dynamo,
    )

    return True


def read(team_id):
    '''
    Returns a Poll object
    '''
    dynamodb = boto3.resource('dynamodb')

    teams_table = dynamodb.Table('lunch_buddies_teams')
    result = teams_table.query(KeyConditionExpression=Key('team_id').eq(team_id))['Items']

    return [
        Poll(
            team_id=item['team_id'],
            created_at_ts=Decimal(item['created_at_ts']),
            created_by_user_id=item['created_by_user_id'],
            callback_id=item['callback_id'],
            state=item['state'],
            created_at=datetime.datetime.strptime(item['created_at'], "%Y-%m-%dT%H:%M:%S.%f"),
            raw=json.loads(item['raw']),
        )
        for item in result
    ]
