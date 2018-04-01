import boto3

from lunch_buddies.constants.queues import QUEUES


def migrate():
    cloudwatch = boto3.client('cloudwatch')
    sns = boto3.client('sns')

    for queue_name in QUEUES.keys():
        alarm_name = '{}_messages_visible'.format(queue_name)

        topic = sns.create_topic(Name=alarm_name)

        print(topic['TopicArn'])

        cloudwatch.put_metric_alarm(
            AlarmName=alarm_name,
            AlarmActions=[topic['TopicArn']],
            MetricName='ApproximateNumberOfMessagesVisible',
            Namespace='AWS/SQS',
            Dimensions=[{'Name': 'QueueName', 'Value': queue_name}],
            Statistic='Max',
            Period=60,
            EvaluationPeriods=1,
            Threshold=1,
            ComparisonOperator='GreaterThanOrEqualToThreshold',
        )
