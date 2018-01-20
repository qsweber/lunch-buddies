import boto3

from lunch_buddies.constants import SQS_QUEUES

if __name__ == '__main__':
    sqs = boto3.client('sqs')

    for queue in SQS_QUEUES:
        sqs.create_queue(QueueName=queue)
