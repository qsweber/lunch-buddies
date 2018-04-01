import logging

from lunch_buddies.constants.queues import (
    POLLS_TO_START,
    USERS_TO_POLL,
    POLLS_TO_CLOSE,
    GROUPS_TO_NOTIFY,
    QUEUES
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

logger = logging.getLogger(__name__)


def _read_from_queue(queue, action, sqs_client, sns_client, slack_client, polls_dao, poll_responses_dao, teams_dao):
    '''
    Pulls messages from the specific queue and passes them to the specified action
    Handles up to 15 messages, but if 3 consecutive iterations result in no message received, exit the loop
    '''
    messages_handled = 0
    consecutive_blanks = 0
    while messages_handled < 15 and consecutive_blanks < 3:
        message, receipt_handle = sqs_client.receive_message(queue)

        if not message:
            consecutive_blanks = consecutive_blanks + 1
            continue

        consecutive_blanks = 0

        try:
            action(message, slack_client, sqs_client, polls_dao, poll_responses_dao, teams_dao)
            sqs_client.delete_message(queue, receipt_handle)
        except Exception as exc:
            logger.error(exc)

        messages_handled = messages_handled + 1

    logger.info('action: {}, messages_handled Handled: {}, consecutive_blanks: {}'.format(
        action.__name__,
        messages_handled,
        consecutive_blanks,
    ))

    check_sqs_and_ping_sns_action(sqs_client, sns_client)

    return messages_handled


def create_poll_from_queue(event, context):
    sqs_client = SqsClient(QUEUES)
    sns_client = SnsClient()
    slack_client = SlackClient()
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()
    teams_dao = TeamsDao()

    return _read_from_queue(
        POLLS_TO_START,
        create_poll_action,
        sqs_client,
        sns_client,
        slack_client,
        polls_dao,
        poll_responses_dao,
        teams_dao,
    )


def poll_users_from_queue(event, context):
    sqs_client = SqsClient(QUEUES)
    sns_client = SnsClient()
    slack_client = SlackClient()
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()
    teams_dao = TeamsDao()

    return _read_from_queue(
        USERS_TO_POLL,
        poll_user_action,
        sqs_client,
        sns_client,
        slack_client,
        polls_dao,
        poll_responses_dao,
        teams_dao,
    )


def close_poll_from_queue(event, context):
    sqs_client = SqsClient(QUEUES)
    sns_client = SnsClient()
    slack_client = SlackClient()
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()
    teams_dao = TeamsDao()

    return _read_from_queue(
        POLLS_TO_CLOSE,
        close_poll_action,
        sqs_client,
        sns_client,
        slack_client,
        polls_dao,
        poll_responses_dao,
        teams_dao,
    )


def notify_groups_from_queue(event, context):
    sqs_client = SqsClient(QUEUES)
    sns_client = SnsClient()
    slack_client = SlackClient()
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()
    teams_dao = TeamsDao()

    return _read_from_queue(
        GROUPS_TO_NOTIFY,
        notify_group_action,
        sqs_client,
        sns_client,
        slack_client,
        polls_dao,
        poll_responses_dao,
        teams_dao,
    )
