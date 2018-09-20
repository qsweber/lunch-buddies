import logging
from typing import Any, List, Optional

from raven import Client
from raven.transport.requests import RequestsHTTPTransport

from lunch_buddies.constants.queues import (
    POLLS_TO_START,
    USERS_TO_POLL,
    POLLS_TO_CLOSE,
    GROUPS_TO_NOTIFY,
    Queue,
)
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.actions.check_sqs_ping_sns import check_sqs_and_ping_sns as check_sqs_and_ping_sns_action
from lunch_buddies.actions.create_poll import create_poll as create_poll_action
from lunch_buddies.actions.close_poll import close_poll as close_poll_action
from lunch_buddies.actions.poll_user import poll_user as poll_user_action
from lunch_buddies.actions.notify_group import notify_group as notify_group_action
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sns import SnsClient
from lunch_buddies.clients.sqs import SqsClient


sentry = Client(transport=RequestsHTTPTransport)
logger = logging.getLogger(__name__)

slack_client = SlackClient()
sqs_client = SqsClient()
sns_client = SnsClient()
teams_dao = TeamsDao()
polls_dao = PollsDao()
poll_responses_dao = PollResponsesDao()


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
        for raw_message, receipt_handle in sqs_client.receive_messages(self.input_queue.queue_name, 15):
            message = self.input_queue.message_type(**raw_message)
            sink_messages = self.handler(message, *self.extras)
            if self.output_queue:
                for sink_message in sink_messages:
                    sqs_client.send_message(self.output_queue.queue_name, sink_message._asdict())
            sqs_client.delete_message(self.input_queue.queue_name, receipt_handle)

        check_sqs_and_ping_sns_action(sqs_client, sns_client)


@captureErrors
def create_poll_from_queue(event: dict, context: dict) -> None:
    polls_to_start_queue_handler = QueueHandler(
        POLLS_TO_START,
        USERS_TO_POLL,
        create_poll_action,
        [slack_client, polls_dao, teams_dao],
    )
    polls_to_start_queue_handler.run()


@captureErrors
def poll_users_from_queue(event: dict, context: dict) -> None:
    users_to_poll_queue_handler = QueueHandler(
        USERS_TO_POLL,
        None,
        poll_user_action,
        [slack_client, polls_dao, teams_dao]
    )
    users_to_poll_queue_handler.run()


@captureErrors
def close_poll_from_queue(event: dict, context: dict) -> None:
    polls_to_close_queue_handler = QueueHandler(
        POLLS_TO_CLOSE,
        GROUPS_TO_NOTIFY,
        close_poll_action,
        [slack_client, polls_dao, poll_responses_dao, teams_dao]
    )
    polls_to_close_queue_handler.run()


@captureErrors
def notify_groups_from_queue(event: dict, context: dict) -> None:
    groups_to_notify_queue_handler = QueueHandler(
        GROUPS_TO_NOTIFY,
        None,
        notify_group_action,
        [slack_client, polls_dao, teams_dao]
    )
    groups_to_notify_queue_handler.run()


@captureErrors
def check_sqs_and_ping_sns(*args) -> None:
    '''
    Runs every minute
    '''
    check_sqs_and_ping_sns_action(sqs_client, sns_client)
