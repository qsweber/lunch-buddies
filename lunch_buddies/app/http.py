import logging
import json
import os

from flask import Flask, jsonify, request, redirect

from lunch_buddies.constants.help import APP_EXPLANATION, CREATE_POLL, CLOSE_POLL
from lunch_buddies.constants.queues import (
    POLLS_TO_START, PollsToStartMessage,
    POLLS_TO_CLOSE, PollsToCloseMessage,
    QUEUES,
    BotMessage,
)
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.actions.auth import auth as auth_action
from lunch_buddies.actions.bot import bot as bot_action
from lunch_buddies.actions.check_sqs_ping_sns import check_sqs_and_ping_sns as check_sqs_and_ping_sns_action
from lunch_buddies.actions.listen_to_poll import listen_to_poll as listen_to_poll_action
from lunch_buddies.actions.create_poll import parse_message_text, InvalidPollOption
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sns import SnsClient
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

    parse_message_text(text)

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
    sns_client = SnsClient()
    teams_dao = TeamsDao()

    request_form = request.form.copy()
    request_form['channel_id'] = None  # This will be filled in later with the default

    outgoing_message = _create_poll(request_form, teams_dao, sqs_client)

    check_sqs_and_ping_sns_action(sqs_client, sns_client)

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
    sns_client = SnsClient()
    teams_dao = TeamsDao()

    request_form = request.form.copy()
    request_form['channel_id'] = None  # This will be filled in later with the default

    outgoing_message = _close_poll(request_form, teams_dao, sqs_client)

    check_sqs_and_ping_sns_action(sqs_client, sns_client)

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


@validate
def _bot(request_form, teams_dao, slack_client, sqs_client, polls_dao, poll_responses_dao):
    bot_action(
        BotMessage(
            team_id=request_form['team_id'],
            channel_id=request_form['event']['channel'],
            user_id=request_form['event']['user'],
            text=request_form['event']['text'],
        ),
        slack_client,
        sqs_client,
        polls_dao,
        poll_responses_dao,
        teams_dao,
    )

    return {'ok': True}


@app.route('/api/v0/bot', methods=['POST'])
def bot_http():
    '''
    Listen to bot mentions
    '''
    request_form = request.form
    logger.info('request.form: {}'.format(request_form))
    if not request_form:
        # TODO: Why?
        logger.info('request.data: {}'.format(json.loads(request.data)))
        request_form = json.loads(request.data)

    teams_dao = TeamsDao()
    polls_dao = PollsDao()
    poll_responses_dao = PollResponsesDao()
    slack_client = SlackClient()
    sqs_client = SqsClient(QUEUES)
    sns_client = SnsClient()

    outgoing_message = _bot(request_form, teams_dao, slack_client, sqs_client, polls_dao, poll_responses_dao)

    check_sqs_and_ping_sns_action(sqs_client, sns_client)

    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


def check_sqs_and_ping_sns():
    '''
    Runs every minute
    '''
    sqs_client = SqsClient(QUEUES)
    sns_client = SnsClient()

    check_sqs_and_ping_sns_action(sqs_client, sns_client)
