from datetime import datetime
import json
import logging
import os
from typing import Tuple, Iterable, List
from uuid import UUID

import boto3

from lunch_buddies.constants.stages import Stage

logger = logging.getLogger(__name__)


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


class SqsClient:
    def _url_for_queue(self, queue_name: str) -> str:
        return 'https://us-west-2.queue.amazonaws.com/120356305272/{}'.format(
            name_for_queue_stage(queue_name, Stage.PROD if os.environ['STAGE'] == Stage.PROD.value else Stage.DEV),
        )

    def _send_message_internal(self, queue_name: str, message: dict) -> None:
        sqs = boto3.client('sqs')
        sqs.send_message(
            QueueUrl=self._url_for_queue(queue_name),
            MessageBody=json.dumps(message, cls=RoundTripEncoder),
        )

    def send_message(self, queue_name: str, message: dict) -> None:
        self._send_message_internal(queue_name, message)

    def send_messages(self, queue_name: str, messages: List[dict]):
        for message in messages:
            self.send_message(queue_name, message)

    def _receive_message_internal(self, **kwargs) -> dict:
        sqs = boto3.client('sqs')
        return sqs.receive_message(**kwargs)

    def receive_messages(self, queue_name: str, maximum: int) -> Iterable[Tuple[dict, str]]:
        count = 0
        consecutive_empty = 0
        url = self._url_for_queue(queue_name)
        while count < maximum and consecutive_empty < 3:
            result = self._receive_message_internal(
                QueueUrl=url,
                MaxNumberOfMessages=1,
                VisibilityTimeout=60,
            )

            if not result or 'Messages' not in result:
                consecutive_empty = consecutive_empty + 1
                continue
            else:
                count = count + 1

            messages = result['Messages']
            message = json.loads(messages[0]['Body'], cls=RoundTripDecoder)
            receipt_handle = messages[0]['ReceiptHandle']

            yield message, receipt_handle

        logger.info('action: {}, count: {}, consecutive_empty: {}'.format(
            url,
            count,
            consecutive_empty,
        ))

    def _delete_message_internal(self, **kwargs) -> None:
        sqs = boto3.client('sqs')
        return sqs.delete_message(**kwargs)

    def delete_message(self, queue_name: str, receipt_handle: str) -> None:
        return self._delete_message_internal(
            QueueUrl=self._url_for_queue(queue_name),
            ReceiptHandle=receipt_handle,
        )

    def message_count(self, queue_name: str) -> int:
        sqs = boto3.resource('sqs')
        sqs_queue = sqs.Queue(self._url_for_queue(queue_name))

        return int(sqs_queue.attributes['ApproximateNumberOfMessages'])


def name_for_queue_stage(queue_name: str, stage: Stage) -> str:
    if stage == Stage.PROD:
        return queue_name
    else:
        return '{}_{}'.format(stage.value, queue_name)
