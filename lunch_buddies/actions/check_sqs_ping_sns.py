import logging

from lunch_buddies.constants.queues import QUEUES


logger = logging.getLogger(__name__)


def check_sqs_and_ping_sns(sqs_client, sns_client):
    for queue, attributes in QUEUES.items():
        if sqs_client.message_count(queue) > 0:
            logger.info('sendming message to {}'.format(attributes['sns_trigger']))
            sns_client.send_message(attributes['sns_trigger'])
