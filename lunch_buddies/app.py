import logging
import json

from flask import Flask, jsonify, request

from lunch_buddies import constants
from lunch_buddies.constants.queues import (
    POLLS_TO_START, PollsToStartMessage,
    USERS_TO_POLL,
    POLLS_TO_CLOSE, PollsToCloseMessage,
    GROUPS_TO_NOTIFY,
)
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.actions.create_poll import create_poll as create_poll_action
from lunch_buddies.actions.close_poll import close_poll as close_poll_action
from lunch_buddies.actions.listen_to_poll import listen_to_poll as listen_to_poll_action
from lunch_buddies.actions.poll_user import poll_user as poll_user_action
from lunch_buddies.actions.notify_group import notify_group as notify_group_action
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sqs import SqsClient

app = Flask(__name__)
logger = logging.getLogger(__name__)


def _create_poll(request_form, sqs_client):
    message = PollsToStartMessage(
        team_id=request_form['team_id'],
        user_id=request_form['user_id'],
    )

    sqs_client.send_message(
        POLLS_TO_START,
        message,
    )

    return True


@app.route('/api/v0/poll/create', methods=['POST'])
def create_poll_http():
    '''
    Create a poll
    This is connected to an incoming slash command from Slack
    '''
    sqs_client = SqsClient(constants.queues.QUEUES)

    _create_poll(request.form, sqs_client)

    outgoing_message = {'text': 'Users will be polled.'}
    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


def _read_from_queue(queue, action, sqs_client, slack_client, polls_dao, poll_responses_dao):
    '''
    Pulls messages from the specific queue and passes them to the specified action
    Handles up to 30 messages, but if 3 consecutive iterations result in no message received, exit the loop
    '''
    messages_handled = 0
    consecutive_blanks = 0
    while messages_handled < 30 and consecutive_blanks < 3:
        message, receipt_handle = sqs_client.receive_message(queue)

        if not message:
            consecutive_blanks = consecutive_blanks + 1
            continue

        consecutive_blanks = 0

        action(message, slack_client, sqs_client, polls_dao, poll_responses_dao)
        sqs_client.delete_message(queue, receipt_handle)

        messages_handled = messages_handled + 1

    return messages_handled


def create_poll_from_queue():
    sqs_client = SqsClient(constants.queues.QUEUES)
    slack_client = SlackClient()
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()

    return _read_from_queue(
        POLLS_TO_START,
        create_poll_action,
        sqs_client,
        slack_client,
        polls_dao,
        poll_responses_dao,
    )


def poll_users_from_queue():
    sqs_client = SqsClient(constants.queues.QUEUES)
    slack_client = SlackClient()
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()

    return _read_from_queue(
        USERS_TO_POLL,
        poll_user_action,
        sqs_client,
        slack_client,
        polls_dao,
        poll_responses_dao,
    )


def _listen_to_poll(request_payload, polls_dao, poll_responses_dao):
    return listen_to_poll_action(request_payload, polls_dao, poll_responses_dao)


@app.route('/api/v0/poll', methods=['POST'])
def listen_to_poll_http():
    '''
    Listens for responses to the poll.
    '''
    request_payload = json.loads(request.form['payload'])
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()

    outgoing_message = _listen_to_poll(request_payload, polls_dao, poll_responses_dao)
    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/poll/close', methods=['POST'])
def close_poll_http():
    '''
    Close a poll
    '''
    sqs_client = SqsClient(constants.queues.QUEUES)
    sqs_client.send_message(
        POLLS_TO_CLOSE,
        PollsToCloseMessage(team_id=request.form['team_id']),
    )

    outgoing_message = {'text': 'Poll will be closed.'}
    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


def close_poll_from_queue():
    return _read_from_queue(POLLS_TO_CLOSE, close_poll_action)


def notify_groups_from_queue():
    return _read_from_queue(GROUPS_TO_NOTIFY, notify_group_action)
