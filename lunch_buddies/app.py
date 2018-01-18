import logging
import json

from flask import Flask, jsonify, request

from lunch_buddies.actions.create_poll import create_poll as create_poll_action
from lunch_buddies.actions.close_poll import close_poll as close_poll_action
from lunch_buddies.actions.listen_to_poll import listen_to_poll as listen_to_poll_action
from lunch_buddies.clients.slack import SlackClient

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route('/api/v0/poll', methods=['POST'])
def listen_to_poll():
    '''
    Listens for responses to the poll
    '''
    request_payload = json.loads(request.form['payload'])

    outgoing_message_payload = listen_to_poll_action(request_payload)

    response = jsonify(outgoing_message_payload)

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/poll/create', methods=['POST'])
def create_poll():
    '''
    Create a poll
    '''
    request_payload = json.loads(json.dumps(request.form))

    slack_client = SlackClient()

    outgoing_message_payload = create_poll_action(request_payload, slack_client)

    response = jsonify(outgoing_message_payload)

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/poll/close', methods=['POST'])
def close_poll():
    '''
    Close a poll
    '''
    request_payload = json.loads(json.dumps(request.form))

    slack_client = SlackClient()

    outgoing_message_payload = close_poll_action(request_payload, slack_client)

    response = jsonify(outgoing_message_payload)

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response
