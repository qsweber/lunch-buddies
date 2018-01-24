import boto3

from lunch_buddies.constants.queues import QUEUES

if __name__ == '__main__':
    sqs = boto3.client('sqs')

    for queue in QUEUES.keys():
        sqs.create_queue(QueueName=queue)
