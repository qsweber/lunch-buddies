import logging

from lunch_buddies.constants.queues import (
    POLLS_TO_START,
    USERS_TO_POLL,
    POLLS_TO_CLOSE,
    GROUPS_TO_NOTIFY,
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
from lunch_buddies.types import PollsToStartMessage, UsersToPollMessage, PollsToCloseMessage, GroupsToNotifyMessage

logger = logging.getLogger(__name__)

slack_client = SlackClient()
sqs_client = SqsClient()
sns_client = SnsClient()
teams_dao = TeamsDao()
polls_dao = PollsDao()
poll_responses_dao = PollResponsesDao()


def create_poll_from_queue(event: dict, context: dict) -> None:
    for raw_message, receipt_handle in sqs_client.receive_messages(POLLS_TO_START, 15):
        message = PollsToStartMessage(**raw_message)
        sink_messages = create_poll_action(message, slack_client, polls_dao, teams_dao)
        for sink_message in sink_messages:
            sqs_client.send_message(USERS_TO_POLL, sink_message._asdict())


def poll_users_from_queue(event: dict, context: dict) -> None:
    for raw_message, receipt_handle in sqs_client.receive_messages(USERS_TO_POLL, 15):
        message = UsersToPollMessage(**raw_message)
        poll_user_action(message, slack_client, polls_dao, teams_dao)


def close_poll_from_queue(event: dict, context: dict) -> None:
    for raw_message, receipt_handle in sqs_client.receive_messages(POLLS_TO_CLOSE, 15):
        message = PollsToCloseMessage(**raw_message)
        sink_messages = close_poll_action(message, slack_client, polls_dao, poll_responses_dao, teams_dao)
        for sink_message in sink_messages:
            sqs_client.send_message(GROUPS_TO_NOTIFY, sink_message._asdict())


def notify_groups_from_queue(event: dict, context: dict) -> None:
    for raw_message, receipt_handle in sqs_client.receive_messages(GROUPS_TO_NOTIFY, 15):
        message = GroupsToNotifyMessage(**raw_message)
        notify_group_action(message, slack_client, polls_dao, teams_dao)


def check_sqs_and_ping_sns() -> None:
    '''
    Runs every minute
    '''
    check_sqs_and_ping_sns_action(sqs_client, sns_client)
