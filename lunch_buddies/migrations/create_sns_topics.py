import boto3

from lunch_buddies.constants.queues import QUEUES


def migrate():
    sns = boto3.client('sns')

    for queue_name in QUEUES.keys():
        alarm_name = '{}_messages_visible'.format(queue_name)

        topic = sns.create_topic(Name=alarm_name)

        print(topic['TopicArn'])
