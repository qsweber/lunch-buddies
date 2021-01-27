import datetime
import uuid
import typing

from lunch_buddies.clients.sqs_v2 import SqsMessage, SqsMessageAttributes


test_input: typing.Dict[str, typing.Any] = {
    "Records": [
        {
            "messageId": "8aa50ffc-1df9-4981-9ef1-46a7878f89dd",
            "receiptHandle": "foo",
            "body": '{"team_id": "1", "channel_id": "2", "user_id": "abc", "text": "def"}',
            "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1583293981975",
                "SenderId": "120356305272",
                "ApproximateFirstReceiveTimestamp": "1583293982030",
            },
            "messageAttributes": {},
            "md5OfBody": "c72b9698fa1927e1dd12d3cf26ed84b2",
            "eventSource": "aws:sqs",
            "eventSourceARN": "arn:aws:sqs:us-west-2:120356305272:dev_test",
            "awsRegion": "us-west-2",
        },
    ],
}

test_output: typing.List[SqsMessage] = [
    SqsMessage(
        message_id=uuid.UUID("8aa50ffc-1df9-4981-9ef1-46a7878f89dd"),
        receipt_handle="foo",
        body={"team_id": "1", "channel_id": "2", "user_id": "abc", "text": "def"},
        attributes=SqsMessageAttributes(
            approximate_receive_count=1,
            sent_timestamp=datetime.datetime(2020, 3, 4, 3, 53, 1, 975000),
            sender_id="120356305272",
            approxmate_first_receive_timestamp=datetime.datetime(
                2020, 3, 4, 3, 53, 2, 30000
            ),
        ),
        md5_of_body="c72b9698fa1927e1dd12d3cf26ed84b2",
        event_source="aws:sqs",
        event_source_arn="arn:aws:sqs:us-west-2:120356305272:dev_test",
        event_source_url="https://sqs.us-west-2.amazonaws.com/120356305272/dev_test",
        aws_region="us-west-2",
    )
]
