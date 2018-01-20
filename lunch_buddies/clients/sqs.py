import json

import boto3

from lunch_buddies import constants


class SqsClient(object):
    def __init__(self):
        self.sqs = boto3.client('sqs')

    def _url_for_queue(self, queue):
        return constants.SQS_QUEUE_URLS[constants.POLLS_TO_START]

    def send_message(self, queue, message):
        return self.sqs.send_message(self._url_for_queue(queue), json.dumps(message))

    def receive_message(self, queue):
        messages = self.sqs.receive_message(self._url_for_queue(queue), MaxNumberOfMessages=1)['Messages']
        if not messages:
            return None

        return json.loads(messages[0]['Body'])
