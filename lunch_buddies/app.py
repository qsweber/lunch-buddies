import logging
import json

from flask import Flask, jsonify, request

from lunch_buddies import constants
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.actions.create_poll import create_poll as create_poll_action
from lunch_buddies.actions.close_poll import close_poll as close_poll_action
from lunch_buddies.actions.listen_to_poll import listen_to_poll as listen_to_poll_action
from lunch_buddies.actions.poll_user import poll_user as poll_user_action
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sqs import SqsClient

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route('/api/v0/poll/create', methods=['POST'])
def create_poll():
    '''
    Create a poll
    '''
    sqs_client = SqsClient()
    sqs_client.send_message(constants.POLLS_TO_START, request.form)

    outgoing_message = {'text': 'Users will be polled.'}
    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


def _read_from_queue(queue, action):
    sqs_client = SqsClient()

    message = sqs_client.receive_message(queue)

    if not message:
        return 'ok', 200

    slack_client = SlackClient()
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()

    outgoing_message = action(message, slack_client, sqs_client, polls_dao, poll_responses_dao)
    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


def create_poll_from_queue():
    return _read_from_queue(constants.POLLS_TO_START, create_poll_action)


def poll_users_from_queue():
    return _read_from_queue(constants.USERS_TO_POLL, poll_user_action)


@app.route('/api/v0/poll', methods=['POST'])
def listen_to_poll():
    '''
    Listens for responses to the poll
    '''
    request_payload = json.loads(request.form['payload'])
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()

    outgoing_message = listen_to_poll_action(request_payload, polls_dao, poll_responses_dao)
    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/poll/close', methods=['POST'])
def close_poll():
    '''
    Close a poll
    '''
    sqs_client = SqsClient()
    sqs_client.send_message(constants.POLLS_TO_CLOSE, request.form)

    outgoing_message = {'text': 'Poll will be closed.'}
    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


def close_poll_from_queue():
    return _read_from_queue(constants.POLLS_TO_CLOSE, close_poll_action)


def notify_groups_from_queue():
    return _read_from_queue(constants.GROUPS_TO_NOTIFY, close_poll_action)
