import logging
import os

from lunch_buddies.clients.sqs import SqsClient, name_for_queue_stage
from lunch_buddies.clients.sns import SnsClient
from lunch_buddies.constants.queues import QUEUES
from lunch_buddies.constants.stages import Stage


logger = logging.getLogger(__name__)


def check_sqs_and_ping_sns(sqs_client: SqsClient, sns_client: SnsClient) -> None:
    for queue in QUEUES:
        if sqs_client.message_count(queue.queue_name) > 0:
            sns_client.send_message(get_sns_trigger_arn(queue.queue_name))


def get_sns_trigger_arn(queue_name: str) -> str:
    return 'arn:aws:sns:us-west-2:120356305272:{}_messages_visible'.format(
        name_for_queue_stage(queue_name, Stage.PROD if os.environ['STAGE'] == Stage.PROD.value else Stage.DEV)
    )
