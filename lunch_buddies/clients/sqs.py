from datetime import datetime
import json
from uuid import UUID

import boto3

from lunch_buddies import constants


class RoundTripEncoder(json.JSONEncoder):
    '''
    Copied from https://gist.github.com/simonw/7000493
    '''
    def default(self, obj):
        if isinstance(obj, datetime):
            return {
                "_type": "datetime",
                "value": obj.timestamp()
            }
        elif isinstance(obj, UUID):
            return {
                "_type": "UUID",
                "value": str(obj)
            }

        return super(RoundTripEncoder, self).default(obj)


class RoundTripDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if '_type' not in obj:
            return obj
        output_type = obj['_type']
        if output_type == 'datetime':
            return datetime.fromtimestamp(obj['value'])
        elif output_type == 'UUID':
            return UUID(obj['value'])
        else:
            return obj


class SqsClient(object):
    def __init__(self):
        self.sqs = boto3.client('sqs')

    def _url_for_queue(self, queue):
        return constants.SQS_QUEUE_URLS[queue]

    def send_message(self, queue, message):
        return self.sqs.send_message(
            QueueUrl=self._url_for_queue(queue),
            MessageBody=json.dumps(message._asdict(), cls=RoundTripEncoder),
        )

    def receive_message(self, queue):
        result = self.sqs.receive_message(
            QueueUrl=self._url_for_queue(queue),
            MaxNumberOfMessages=1,
            VisibilityTimeout=60,
        )
        if not result or 'Messages' not in result:
            return None, None

        messages = result['Messages']

        message_object = constants.SQS_QUEUE_INTERFACES[queue](**json.loads(messages[0]['Body'], cls=RoundTripDecoder))

        return message_object, messages[0]['ReceiptHandle']

    def delete_message(self, queue, receipt_handle):
        return self.sqs.delete_message(
            QueueUrl=self._url_for_queue(queue),
            ReceiptHandle=receipt_handle,
        )
