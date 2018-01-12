import datetime
from decimal import Decimal
import json

import boto3
from boto3.dynamodb.conditions import Key

from lunch_buddies.models.messages import Message


def add(message):
    dynamodb = boto3.resource('dynamodb')

    # add team
    teams_table = dynamodb.Table('lunch_buddies_teams')
    team_for_dynamo = {
        'team_id': message.team_id,
        'channel_id': message.channel_id,
    }
    teams_table.put_item(
        Item=team_for_dynamo,
    )

    # add message
    messages_table = dynamodb.Table('lunch_buddies_messages')
    message_for_dynamo = {
        'team_id_channel_id': '{}-{}'.format(message.team_id, message.channel_id),
        'message_ts': Decimal(message.message_ts),
        'from_user_id': message.from_user_id,
        'to_user_id': message.to_user_id,
        'received_at': message.received_at.isoformat(),
        'type': message.type,
        'raw': json.dumps(message.raw),
    }
    messages_table.put_item(
        Item=message_for_dynamo,
    )

    return True


def get(team_id, channel_id=None):
    '''
    Returns a list of Message objects
    '''
    dynamodb = boto3.resource('dynamodb')

    teams_table = dynamodb.Table('lunch_buddies_teams')
    result = teams_table.query(KeyConditionExpression=Key('team_id').eq(team_id))['Items']

    if channel_id:
        result = [
          item
          for item in result
          if item['channel_id'] == channel_id
        ]

    messages_table = dynamodb.Table('lunch_buddies_messages')

    messages = []
    for item in result:
        user_messages = messages_table.query(
            KeyConditionExpression=Key('team_id_channel_id').eq('{}-{}'.format(item['team_id'], item['channel_id']))
        )['Items']

        for raw_message in user_messages:
            messages.append(Message(
                team_id=raw_message['team_id_channel_id'].split('-')[0],
                channel_id=raw_message['team_id_channel_id'].split('-')[1],
                message_ts=raw_message['message_ts'],
                from_user_id=raw_message['from_user_id'],
                to_user_id=raw_message['to_user_id'],
                received_at=datetime.datetime.strptime(raw_message['received_at'], "%Y-%m-%dT%H:%M:%S.%f"),
                type=raw_message['type'],
                raw=json.loads(raw_message['raw']),
            ))

    return messages
