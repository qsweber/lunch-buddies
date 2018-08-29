import boto3


class SnsClient(object):
    def send_message(self, arn: str) -> None:
        sns = boto3.resource('sns')
        topic = sns.Topic(arn)
        topic.publish(Message='string')
