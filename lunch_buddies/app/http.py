import logging
import json
import os
from typing import Tuple
from uuid import UUID

from flask import Flask, jsonify, request, redirect
from raven import Client
from raven.contrib.flask import Sentry
from raven.transport.requests import RequestsHTTPTransport

from lunch_buddies.constants.help import APP_EXPLANATION
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.groups import GroupsDao
from lunch_buddies.actions.auth import auth as auth_action
from lunch_buddies.actions.bot import bot as bot_action
from lunch_buddies.actions.check_sqs_ping_sns import check_sqs_and_ping_sns as check_sqs_and_ping_sns_action
from lunch_buddies.actions.listen_to_poll import listen_to_poll as listen_to_poll_action
from lunch_buddies.actions.queue_close_poll import queue_close_poll
from lunch_buddies.actions.queue_create_poll import queue_create_poll
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sns import SnsClient
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.clients.http import HttpClient
from lunch_buddies.types import Auth, BotMention, ClosePoll, CreatePoll, ListenToPoll

app = Flask(__name__)
sentry = Sentry(
    app,
    client=Client(
        transport=RequestsHTTPTransport,
    ),
)
logger = logging.getLogger(__name__)

slack_client = SlackClient()
sqs_client = SqsClient()
sns_client = SnsClient()
http_client = HttpClient()
teams_dao = TeamsDao()
polls_dao = PollsDao()
poll_responses_dao = PollResponsesDao()
groups_dao = GroupsDao()


def _validate_request_token(token: str) -> bool:
    if (token != os.environ['VERIFICATION_TOKEN'] and token != os.environ['VERIFICATION_TOKEN_DEV']):
        raise Exception('you are not authorized to call this URL')

    return True


def _validate_team(team_id: str, teams_dao: TeamsDao) -> bool:
    if not teams_dao.read('team_id', team_id):
        raise Exception('your team is not authorized for this app')

    return True


@app.route('/api/v0/poll/create', methods=['POST'])
def create_poll_http() -> str:
    '''
    Create a poll
    This is connected to an incoming slash command from Slack
    '''
    _validate_request_token(request.form['token'])
    _validate_team(request.form['team_id'], teams_dao)

    request_form = CreatePoll(
        text=request.form['text'],
        team_id=request.form['team_id'],
        user_id=request.form['user_id'],
        channel_id='',  # This will be filled in later with the default
    )

    outgoing_text = queue_create_poll(request_form, sqs_client)

    check_sqs_and_ping_sns_action(sqs_client, sns_client)

    response = jsonify({'text': outgoing_text})
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/poll', methods=['POST'])
def listen_to_poll_http() -> str:
    '''
    Listens for responses to the poll.
    '''
    payload = json.loads(request.form['payload'])
    _validate_request_token(payload['token'])

    request_form = ListenToPoll(
        original_message=payload['original_message'].copy(),
        team_id=payload['team']['id'],
        user_id=payload['user']['id'],
        choice_key=payload['actions'][0]['value'],
        action_ts=float(payload['action_ts']),
        callback_id=UUID(payload['callback_id']),
    )

    outgoing_message = listen_to_poll_action(request_form, polls_dao, poll_responses_dao)

    response = jsonify(outgoing_message)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/poll/close', methods=['POST'])
def close_poll_http() -> str:
    '''
    Close a poll
    '''
    _validate_request_token(request.form['token'])
    _validate_team(request.form['team_id'], teams_dao)

    request_form = ClosePoll(
        team_id=request.form['team_id'],
        channel_id='',
        user_id=request.form['user_id'],
        text=request.form['text'],
    )

    outgoing_message = queue_close_poll(request_form, sqs_client)

    check_sqs_and_ping_sns_action(sqs_client, sns_client)

    response = jsonify({'text': outgoing_message})
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/help', methods=['POST'])
def help_http() -> str:
    '''
    Explains the app.
    '''
    _validate_request_token(request.form['token'])
    _validate_team(request.form['team_id'], teams_dao)

    response = jsonify({'text': APP_EXPLANATION})
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/api/v0/install', methods=['GET'])
def install_http() -> str:
    '''
    Install a new workspace
    '''
    return redirect(os.environ['AUTH_URL'])


@app.route('/api/v0/auth', methods=['GET'])
def auth_http() -> str:
    '''
    Authorize a new workspace
    '''
    request_form = Auth(
        code=request.args['code'],
    )

    auth_action(request_form, teams_dao, slack_client, http_client)

    return redirect('http://lunchbuddies.quinnweber.com/registration/')


@app.route('/api/v0/bot', methods=['POST'])
def bot_http() -> Tuple[str, int]:
    '''
    Listen to bot mentions
    '''
    raw_request_form = request.form or json.loads(request.data)

    _validate_request_token(raw_request_form['token'])
    _validate_team(raw_request_form['team_id'], teams_dao)

    request_form = BotMention(
        team_id=raw_request_form['team_id'],
        channel_id=raw_request_form['event']['channel'],
        user_id=raw_request_form['event']['user'],
        text=raw_request_form['event']['text'],
    )

    bot_action(
        request_form,
        sqs_client,
        slack_client,
        teams_dao,
        polls_dao,
        groups_dao,
    )

    check_sqs_and_ping_sns_action(sqs_client, sns_client)

    return 'ok', 200


@app.route('/api/v0/error', methods=['GET'])
def error_http() -> str:
    '''
    Test error handler
    '''
    raise Exception('test error')
