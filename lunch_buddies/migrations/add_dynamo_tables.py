import boto3

if __name__ == '__main__':
    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

    polls = dynamodb.create_table(
        TableName='lunch_buddies_Poll',
        KeySchema=[
            {
                'AttributeName': 'team_id',  # globally unique partition
                'KeyType': 'HASH',
            },
            {
                'AttributeName': 'created_at',
                'KeyType': 'RANGE',
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'team_id',
                'AttributeType': 'S',
            },
            {
                'AttributeName': 'created_at',
                'AttributeType': 'N',
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    polls.meta.client.get_waiter('table_exists').wait(TableName='lunch_buddies_Poll')

    poll_responses = dynamodb.create_table(
        TableName='lunch_buddies_PollResponse',
        KeySchema=[
            {
                'AttributeName': 'callback_id',  # globally unique partition
                'KeyType': 'HASH',
            },
            {
                'AttributeName': 'user_id',
                'KeyType': 'RANGE',
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'callback_id',
                'AttributeType': 'S',
            },
            {
                'AttributeName': 'user_id',
                'AttributeType': 'S',
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    poll_responses.meta.client.get_waiter('table_exists').wait(TableName='lunch_buddies_PollResponse')

    team = dynamodb.create_table(
        TableName='lunch_buddies_Team',
        KeySchema=[
            {
                'AttributeName': 'team_id',
                'KeyType': 'HASH',
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'team_id',
                'AttributeType': 'S',
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

    team.meta.client.get_waiter('table_exists').wait(TableName='lunch_buddies_Team')
