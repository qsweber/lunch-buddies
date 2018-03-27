import logging
import json
import os

from flask import Flask, jsonify, request, redirect

from lunch_buddies.constants.help import APP_EXPLANATION, CREATE_POLL, CLOSE_POLL
from lunch_buddies.constants.queues import (
    POLLS_TO_START, PollsToStartMessage,
    POLLS_TO_CLOSE, PollsToCloseMessage,
    QUEUES,
)
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.actions.auth import auth as auth_action
from lunch_buddies.actions.listen_to_poll import listen_to_poll as listen_to_poll_action
from lunch_buddies.actions.create_poll import get_choices_from_message_text, InvalidPollOption
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sqs import SqsClient


app = Flask(__name__)
logger = logging.getLogger(__name__)


def _validate_request_token(request_form):
    if (
        request_form['token'] != os.environ['VERIFICATION_TOKEN'] and
        request_form['token'] != os.environ['VERIFICATION_TOKEN_DEV']
    ):
        raise Exception('you are not authorized to call this URL')

    return True


def _validate_team(request_form, teams_dao):
    if 'team_id' in request_form:
        team_id = request_form['team_id']
    else:
        team_id = request_form['team']['id']

    if not teams_dao.read('team_id', team_id):
        raise Exception('your team is not authorized for this app')


def _is_help(request_form):
    return request_form['text'].lower().strip() == 'help'


def validate(func):
    def wrapper(request_form, teams_dao, *args, **kwargs):
        _validate_request_token(request_form)
        _validate_team(request_form, teams_dao)

        return func(request_form, teams_dao, *args, **kwargs)

    return wrapper


def validate_create_poll(request_form):
    text = request_form['text']

    get_choices_from_message_text(text)

    return True


@validate
def _create_poll(request_form, teams_dao, sqs_client):
    if _is_help(request_form):
        return {'text': CREATE_POLL}

    try:
        validate_create_poll(request_form)
    except InvalidPollOption as e:
        return {'text': 'Failed: {}'.format(str(e))}

    message = PollsToStartMessage(
        team_id=request_form['team_id'],
        channel_id=request_form['channel_id'],
        user_id=request_form['user_id'],
        text=request_form['text'],
    )

    sqs_client.send_message(
        POLLS_TO_START,
        message,
    )

    return {'text': 'Users will be polled.'}


@app.route('/api/v0/poll/create', methods=['POST'])
def create_poll_http():
    '''
    Create a poll
    This is connected to an incoming slash command from Slack
    '''
    sqs_client = SqsClient(QUEUES)
    teams_dao = TeamsDao()

    request_form = request.form
    request_form['channel_id'] = None  # This will be filled in later with the default

    outgoing_message = _create_poll(request_form, teams_dao, sqs_client)

    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@validate
def _listen_to_poll(request_form, teams_dao, polls_dao, poll_responses_dao):
    return listen_to_poll_action(request_form, polls_dao, poll_responses_dao)


@app.route('/api/v0/poll', methods=['POST'])
def listen_to_poll_http():
    '''
    Listens for responses to the poll.
    '''
    request_form = json.loads(request.form['payload'])
    teams_dao = TeamsDao()
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()

    outgoing_message = _listen_to_poll(request_form, teams_dao, polls_dao, poll_responses_dao)
    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@validate
def _close_poll(request_form, teams_dao, sqs_client):
    if _is_help(request_form):
        return {'text': CLOSE_POLL}

    sqs_client.send_message(
        POLLS_TO_CLOSE,
        PollsToCloseMessage(
            team_id=request_form['team_id'],
            channel_id=request_form['channel_id'],
            user_id=request_form['user_id'],
        )
    )

    return {'text': 'Poll will be closed.'}


@app.route('/api/v0/poll/close', methods=['POST'])
def close_poll_http():
    '''
    Close a poll
    '''
    sqs_client = SqsClient(QUEUES)
    teams_dao = TeamsDao()

    request_form = request.form
    request_form['channel_id'] = None  # This will be filled in later with the default

    outgoing_message = _close_poll(request_form, teams_dao, sqs_client)

    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@validate
def _help(request_form, teams_dao):
    return {'text': APP_EXPLANATION}


@app.route('/api/v0/help', methods=['POST'])
def help_http():
    '''
    Explains the app.
    '''
    teams_dao = TeamsDao()
    outgoing_message = _help(request.form, teams_dao)

    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/install', methods=['GET'])
def install_http():
    '''
    Install a new workspace
    '''
    return redirect(os.environ['AUTH_URL'])


@app.route('/api/v0/auth', methods=['GET'])
def auth_http():
    '''
    Authorize a new workspace
    '''
    teams_dao = TeamsDao()
    slack_client = SlackClient()

    auth_action(request.args, teams_dao, slack_client)

    return redirect('http://lunchbuddies.quinnweber.com/registration/')
