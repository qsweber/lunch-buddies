import logging
from typing import cast, List, NamedTuple

from raven import Client
from raven.transport.requests import RequestsHTTPTransport

from lunch_buddies.clients.sqs_v2 import SqsMessage
from lunch_buddies.actions.create_poll import create_poll as create_poll_action
from lunch_buddies.actions.close_poll import close_poll as close_poll_action
from lunch_buddies.actions.poll_user import poll_user as poll_user_action
from lunch_buddies.actions.notify_group import notify_group as notify_group_action
from lunch_buddies.actions.invoice import invoice as invoice_action
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.types import (
    PollsToCloseMessage,
    PollsToStartMessage,
    UsersToPollMessage,
    GroupsToNotifyMessage,
)


sentry = Client(transport=RequestsHTTPTransport)
logger = logging.getLogger(__name__)


def sqsHandler(func):
    def wrapper(event: dict, context: dict):
        messages = service_context.clients.sqs_v2.parse_sqs_messages(event)
        for message in messages:
            try:
                func(message)
            except Exception:
                service_context.clients.sqs_v2.set_visibility_timeout_with_backoff(
                    message
                )
                sentry.captureException()
                raise

    return wrapper


@sqsHandler
def create_poll_from_queue(message: SqsMessage) -> None:
    output_messages = create_poll_action(
        PollsToStartMessage(**message.body),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )

    # Read this for why we have to do the cast
    # https://github.com/python/mypy/issues/2984
    service_context.clients.sqs_v2.send_messages(
        "users_to_poll", cast(List[NamedTuple], output_messages)
    )


@sqsHandler
def poll_users_from_queue(message: SqsMessage) -> None:
    poll_user_action(
        UsersToPollMessage(**message.body),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )


@sqsHandler
def close_poll_from_queue(message: SqsMessage) -> None:
    output_messages = close_poll_action(
        PollsToCloseMessage(**message.body),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.poll_responses,
        service_context.daos.teams,
    )

    # Read this for why we have to do the cast
    # https://github.com/python/mypy/issues/2984
    service_context.clients.sqs_v2.send_messages(
        "groups_to_notify", cast(List[NamedTuple], output_messages)
    )


@sqsHandler
def notify_groups_from_queue(message: SqsMessage) -> None:
    notify_group_action(
        GroupsToNotifyMessage(**message.body),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
        service_context.daos.groups,
    )


@sqsHandler
def error_queue(message: SqsMessage) -> None:
    raise Exception("Test of error handling")


def invoice(*args) -> None:
    invoice_action(service_context, True)
