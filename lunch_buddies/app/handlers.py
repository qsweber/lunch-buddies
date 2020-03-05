import json
import logging
from typing import cast, Any, List, Optional, NamedTuple

from raven import Client
from raven.transport.requests import RequestsHTTPTransport

from lunch_buddies.clients.sqs_v2 import SqsClient
from lunch_buddies.constants.queues import (
    # POLLS_TO_START,
    USERS_TO_POLL,
    POLLS_TO_CLOSE,
    GROUPS_TO_NOTIFY,
    Queue,
)
from lunch_buddies.actions.check_sqs_ping_sns import check_sqs_and_ping_sns as check_sqs_and_ping_sns_action
from lunch_buddies.actions.create_poll import create_poll as create_poll_action
from lunch_buddies.actions.close_poll import close_poll as close_poll_action
from lunch_buddies.actions.poll_user import poll_user as poll_user_action
from lunch_buddies.actions.notify_group import notify_group as notify_group_action
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.types import (
    # PollsToCloseMessage,
    PollsToStartMessage,
    # UsersToPollMessage,
    # GroupsToNotifyMessage,
)


sentry = Client(transport=RequestsHTTPTransport)
logger = logging.getLogger(__name__)
sqs_client_v2 = SqsClient()


def captureErrors(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            sentry.captureException()
            raise

    return wrapper


class QueueHandler:
    def __init__(self, input_queue: Queue, output_queue: Optional[Queue], handler: Any, extras: List[Any]) -> None:
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.handler = handler
        self.extras = extras

    def run(self) -> None:
        for raw_message, receipt_handle in service_context.clients.sqs.receive_messages(self.input_queue.queue_name, 15):
            message = self.input_queue.message_type(**raw_message)
            sink_messages = self.handler(message, *self.extras)
            if self.output_queue:
                for sink_message in sink_messages:
                    service_context.clients.sqs.send_message(self.output_queue.queue_name, sink_message._asdict())
            service_context.clients.sqs.delete_message(self.input_queue.queue_name, receipt_handle)

        check_sqs_and_ping_sns_action(service_context.clients.sqs, service_context.clients.sns)


@captureErrors
def create_poll_from_queue(event: dict, context: dict) -> None:
    messages = sqs_client_v2.parse_sqs_messages(event)

    for message in messages:
        output_messages = create_poll_action(
            PollsToStartMessage(**message.body),
            service_context.clients.slack,
            service_context.daos.polls,
            service_context.daos.teams,
        )

        # Read this for why we have to do the cast
        # https://github.com/python/mypy/issues/2984
        sqs_client_v2.send_messages('users_to_poll', cast(List[NamedTuple], output_messages))

        sqs_client_v2.delete_message(message)


@captureErrors
def poll_users_from_queue(event: dict, context: dict) -> None:
    users_to_poll_queue_handler = QueueHandler(
        USERS_TO_POLL,
        None,
        poll_user_action,
        [service_context.clients.slack, service_context.daos.polls, service_context.daos.teams]
    )
    users_to_poll_queue_handler.run()


@captureErrors
def close_poll_from_queue(event: dict, context: dict) -> None:
    polls_to_close_queue_handler = QueueHandler(
        POLLS_TO_CLOSE,
        GROUPS_TO_NOTIFY,
        close_poll_action,
        [service_context.clients.slack, service_context.daos.polls, service_context.daos.poll_responses, service_context.daos.teams]
    )
    polls_to_close_queue_handler.run()


@captureErrors
def notify_groups_from_queue(event: dict, context: dict) -> None:
    groups_to_notify_queue_handler = QueueHandler(
        GROUPS_TO_NOTIFY,
        None,
        notify_group_action,
        [service_context.clients.slack, service_context.daos.polls, service_context.daos.teams, service_context.daos.team_settings, service_context.daos.groups]
    )
    groups_to_notify_queue_handler.run()


@captureErrors
def check_sqs_and_ping_sns(*args) -> None:
    '''
    Runs every minute
    '''
    check_sqs_and_ping_sns_action(service_context.clients.sqs, service_context.clients.sns)


def sqs_test(event: dict, context: dict) -> None:
    logger.info(json.dumps(event, default=str))
    logger.info(json.dumps(context, default=str))

    logger.info('Done!')
