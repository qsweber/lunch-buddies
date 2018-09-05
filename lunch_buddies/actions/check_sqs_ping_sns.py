import logging

from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.clients.sns import SnsClient
from lunch_buddies.constants.queues import QUEUES


logger = logging.getLogger(__name__)


def check_sqs_and_ping_sns(sqs_client: SqsClient, sns_client: SnsClient) -> None:
    for queue, attributes in QUEUES.items():
        if sqs_client.message_count(queue) > 0:
            sns_client.send_message(attributes.sns_trigger)
