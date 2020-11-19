import logging
import json
import os
from typing import Tuple, cast, List, NamedTuple
from uuid import UUID

from flask import Flask, jsonify, request, redirect, Response
from raven import Client  # type: ignore
from raven.contrib.flask import Sentry  # type: ignore
from raven.transport.requests import RequestsHTTPTransport  # type: ignore
from werkzeug import Response as WResponse

from lunch_buddies.constants.help import APP_EXPLANATION
from lunch_buddies.actions.oauth2 import oauth2 as oauth2_action
from lunch_buddies.actions.bot import bot as bot_action, parse_raw_request
from lunch_buddies.actions.listen_to_poll import listen_to_poll as listen_to_poll_action
from lunch_buddies.actions.queue_close_poll import queue_close_poll
from lunch_buddies.actions.queue_create_poll import queue_create_poll
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.types import Auth, ClosePoll, CreatePoll, ListenToPoll
from lunch_buddies.lib.service_context import service_context


app = Flask(__name__)
sentry = Sentry(
    app,
    client=Client(
        transport=RequestsHTTPTransport,
    ),
)
logger = logging.getLogger(__name__)


def _validate_request_token(token: str) -> bool:
    if (
        token != os.environ["VERIFICATION_TOKEN"]
        and token != os.environ["VERIFICATION_TOKEN_DEV"]
    ):
        raise Exception("you are not authorized to call this URL")

    return True


def _validate_team(team_id: str, teams_dao: TeamsDao) -> bool:
    if not teams_dao.read("team_id", team_id):
        raise Exception("your team is not authorized for this app")

    return True


@app.route("/api/v0/poll/create", methods=["POST"])
def create_poll_http() -> Response:
    """
    Create a poll
    This is connected to an incoming slash command from Slack
    """
    _validate_request_token(request.form["token"])
    _validate_team(request.form["team_id"], service_context.daos.teams)

    request_form = CreatePoll(
        text=request.form["text"],
        team_id=request.form["team_id"],
        user_id=request.form["user_id"],
        channel_id=None,  # This will be filled in later with the default
    )

    outgoing_text = queue_create_poll(request_form, service_context)

    response = jsonify({"text": outgoing_text})
    response.headers.add("Access-Control-Allow-Origin", "*")

    return cast(Response, response)


@app.route("/api/v0/poll", methods=["POST"])
def listen_to_poll_http() -> Response:
    """
    Listens for responses to the poll.
    """
    payload = json.loads(request.form["payload"])
    _validate_request_token(payload["token"])

    request_form = ListenToPoll(
        original_message=payload["original_message"].copy(),
        team_id=payload["team"]["id"],
        user_id=payload["user"]["id"],
        choice_key=payload["actions"][0]["value"],
        action_ts=float(payload["action_ts"]),
        callback_id=UUID(payload["callback_id"]),
    )

    outgoing_message = listen_to_poll_action(
        request_form, service_context.daos.polls, service_context.daos.poll_responses
    )

    response = jsonify(outgoing_message)
    response.headers.add("Access-Control-Allow-Origin", "*")

    return cast(Response, response)


@app.route("/api/v0/poll/close", methods=["POST"])
def close_poll_http() -> Response:
    """
    Close a poll
    """
    _validate_request_token(request.form["token"])
    _validate_team(request.form["team_id"], service_context.daos.teams)

    request_form = ClosePoll(
        team_id=request.form["team_id"],
        channel_id="",
        user_id=request.form["user_id"],
        text=request.form["text"],
    )

    outgoing_message = queue_close_poll(request_form, service_context)

    response = jsonify({"text": outgoing_message})
    response.headers.add("Access-Control-Allow-Origin", "*")

    return cast(Response, response)


@app.route("/api/v0/help", methods=["POST"])
def help_http() -> Response:
    """
    Explains the app.
    """
    _validate_request_token(request.form["token"])
    _validate_team(request.form["team_id"], service_context.daos.teams)

    response = jsonify({"text": APP_EXPLANATION})
    response.headers.add("Access-Control-Allow-Origin", "*")

    return cast(Response, response)


@app.route("/api/v0/install", methods=["GET"])
def install_http() -> WResponse:
    """
    Install a new workspace
    """
    logger.info("{} {}".format(request.url, json.dumps(request.args)))
    return redirect(os.environ["AUTH_URL"])


@app.route("/api/v0/auth", methods=["GET"])
def auth_http() -> WResponse:
    """
    Authorize a new workspace
    """
    logger.info("{} {}".format(request.url, json.dumps(request.args)))

    request_form = Auth(
        code=request.args["code"],
    )

    oauth2_action(request_form, service_context)

    return redirect("https://www.lunchbuddiesapp.com/registration/")


@app.route("/api/v0/bot", methods=["POST"])
def bot_http() -> Tuple[str, int]:
    """
    Listen to bot mentions
    """
    raw_request_form = request.form or json.loads(request.data)

    _validate_request_token(raw_request_form["token"])
    _validate_team(raw_request_form["team_id"], service_context.daos.teams)

    request_form = parse_raw_request(raw_request_form)

    bot_action(
        request_form,
        service_context,
    )

    return "ok", 200


@app.route("/api/v0/error", methods=["GET"])
def error_http() -> str:
    """
    Test error handler
    """
    service_context.clients.sqs_v2.send_messages(
        "error", cast(List[NamedTuple], [Auth(code="1234")])
    )
    raise Exception("test error")
