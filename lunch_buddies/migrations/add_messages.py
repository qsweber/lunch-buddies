import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

if __name__ == '__main__':
    messages = dynamodb.create_table(
        TableName='lunch_buddies_messages',
        KeySchema=[
            {
                'AttributeName': 'team_id_channel_id',  # globally unique partition
                'KeyType': 'HASH',
            },
            {
                'AttributeName': 'message_ts',
                'KeyType': 'RANGE',
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'team_id_channel_id',
                'AttributeType': 'S',
            },
            {
                'AttributeName': 'message_ts',
                'AttributeType': 'N',
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    messages.meta.client.get_waiter('table_exists').wait(TableName='lunch_buddies_messages')

    teams = dynamodb.create_table(
        TableName='lunch_buddies_teams',
        KeySchema=[
            {
                'AttributeName': 'team_id',  # globally unique partition
                'KeyType': 'HASH',
            },
            {
                'AttributeName': 'channel_id',
                'KeyType': 'RANGE',
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'team_id',
                'AttributeType': 'S',
            },
            {
                'AttributeName': 'channel_id',
                'AttributeType': 'S',
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    teams.meta.client.get_waiter('table_exists').wait(TableName='lunch_buddies_teams')

    polls = dynamodb.create_table(
        TableName='lunch_buddies_polls',
        KeySchema=[
            {
                'AttributeName': 'team_id',  # globally unique partition
                'KeyType': 'HASH',
            },
            {
                'AttributeName': 'created_at_ts',
                'KeyType': 'RANGE',
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'team_id',
                'AttributeType': 'S',
            },
            {
                'AttributeName': 'created_at_ts',
                'AttributeType': 'N',
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    polls.meta.client.get_waiter('table_exists').wait(TableName='lunch_buddies_polls')
