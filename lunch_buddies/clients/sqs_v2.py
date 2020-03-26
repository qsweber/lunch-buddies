from datetime import datetime
import json
import logging
import os
from typing import NamedTuple, List
from uuid import UUID

import boto3

from lunch_buddies.constants.stages import Stage

logger = logging.getLogger(__name__)


class SqsMessageAttributes(NamedTuple):
    approximate_receive_count: int
    sent_timestamp: datetime
    sender_id: str
    approxmate_first_receive_timestamp: datetime


class SqsMessage(NamedTuple):
    message_id: UUID
    receipt_handle: str
    body: dict
    attributes: SqsMessageAttributes
    md5_of_body: str
    event_source: str
    event_source_arn: str
    event_source_url: str
    aws_region: str


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
    def __init__(self, fake: bool = False) -> None:
        if not fake:
            self.sqs = boto3.client('sqs')
        else:
            self.sqs = None

    def _name_for_queue_stage(self, queue_name: str, stage: Stage) -> str:
        if stage == Stage.PROD:
            return queue_name
        else:
            return '{}_{}'.format(stage.value, queue_name)

    def _url_for_queue(self, queue_name: str) -> str:
        return 'https://us-west-2.queue.amazonaws.com/120356305272/{}'.format(
            self._name_for_queue_stage(queue_name, Stage.PROD if os.environ['STAGE'] == Stage.PROD.value else Stage.DEV),
        )

    def _url_from_arn(self, arn: str) -> str:
        arn_parts = arn.split(':')
        region = arn_parts[3]
        account_id = arn_parts[4]
        queue_name = arn_parts[5]
        return 'https://sqs.{}.amazonaws.com/{}/{}'.format(
            region,
            account_id,
            queue_name,
        )

    def _parse_sqs_message(self, raw: dict) -> SqsMessage:
        return SqsMessage(
            message_id=UUID(raw['messageId']),
            receipt_handle=raw['receiptHandle'],
            body=json.loads(raw['body'], cls=RoundTripDecoder),
            attributes=SqsMessageAttributes(
                approximate_receive_count=int(raw['attributes']['ApproximateReceiveCount']),
                sent_timestamp=datetime.utcfromtimestamp(float(raw['attributes']['SentTimestamp']) / 1000),
                sender_id=raw['attributes']['SenderId'],
                approxmate_first_receive_timestamp=datetime.utcfromtimestamp(float(raw['attributes']['ApproximateFirstReceiveTimestamp']) / 1000),
            ),
            md5_of_body=raw['md5OfBody'],
            event_source=raw['eventSource'],
            event_source_arn=raw['eventSourceARN'],
            event_source_url=self._url_from_arn(raw['eventSourceARN']),
            aws_region=raw['awsRegion'],
        )

    def parse_sqs_messages(self, raw: dict) -> List[SqsMessage]:
        return [
            self._parse_sqs_message(m)
            for m in raw['Records']
        ]

    def _send_message_internal(self, queue_name: str, message: NamedTuple) -> None:
        self.sqs.send_message(
            QueueUrl=self._url_for_queue(queue_name),
            MessageBody=json.dumps(message._asdict(), cls=RoundTripEncoder),
        )

    def send_messages(self, queue_name: str, messages: List[NamedTuple]):
        for message in messages:
            self._send_message_internal(queue_name, message)

    def set_visibility_timeout_with_backoff(self, sqs_message: SqsMessage) -> None:
        backoff = min(sqs_message.attributes.approximate_receive_count * 10, 600)
        return self.sqs.change_message_visibility(
            QueueUrl=sqs_message.event_source_url,
            ReceiptHandle=sqs_message.receipt_handle,
            VisibilityTimeout=backoff,
        )
