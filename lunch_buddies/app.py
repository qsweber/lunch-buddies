import datetime
import logging
import json
import os

from flask import Flask, jsonify, request

from lunch_buddies.actions import poll_users
from lunch_buddies.dao import messages as messages_dao
from lunch_buddies.models.messages import Message

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route('/api/v0/poll', methods=['POST'])
def index():
    request_payload = json.loads(request.form['payload'])

    incoming_message = Message(
        team_id=request_payload['team']['id'],
        channel_id=request_payload['channel']['id'],
        message_ts=request_payload['action_ts'],
        from_user_id=request_payload['user']['id'],
        to_user_id=os.environ['BOT_USER_ID'],
        received_at=datetime.datetime.now(),
        type='POLL_RESPONSE',
        raw=request_payload,
    )
    messages_dao.add(incoming_message)

    if request_payload['type'] == 'interactive_message':
        poll_users.poll_listener(incoming_message)

    response = jsonify({
        'foo': 2,
        'bar': 2,
    })

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/poll/administer', methods=['POST'])
def administer():
    pass
