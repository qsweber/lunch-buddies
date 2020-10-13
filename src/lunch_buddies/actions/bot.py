import json
import logging
import re
from typing import Optional, Tuple

from lunch_buddies.actions.queue_create_poll import queue_create_poll
from lunch_buddies.actions.queue_close_poll import queue_close_poll
from lunch_buddies.actions.get_summary import get_summary
from lunch_buddies.constants.help import APP_EXPLANATION
from lunch_buddies.types import BotMention, ClosePoll, CreatePoll
from lunch_buddies.lib.service_context import ServiceContext


logger = logging.getLogger(__name__)


def bot(
    message: BotMention,
    service_context: ServiceContext,
) -> None:
    logger.info("Input: {}".format(message.text))

    parsed_text = _parse_message(message)

    if not parsed_text:
        return

    team = service_context.daos.teams.read_one_or_die("team_id", message.team_id)

    first_word, rest_of_command = parsed_text
    logger.info(
        "First word: {}, Rest of command: {}".format(
            first_word,
            rest_of_command,
        )
    )

    if first_word == "create":
        response_text = queue_create_poll(
            CreatePoll(
                text=rest_of_command,
                team_id=message.team_id,
                channel_id=message.channel_id,
                user_id=message.user_id,
            ),
            service_context,
        )
    elif first_word == "close":
        response_text = queue_close_poll(
            ClosePoll(
                team_id=message.team_id,
                channel_id=message.channel_id,
                user_id=message.user_id,
                text=rest_of_command,
            ),
            service_context,
        )
    elif first_word == "summary":
        response_text = get_summary(
            message=message,
            rest_of_command=rest_of_command,
            team=team,
            service_context=service_context,
        )
    elif first_word == "help":
        response_text = APP_EXPLANATION
    else:
        response_text = ""

    service_context.clients.slack.post_message(
        bot_access_token=team.bot_access_token,
        channel=message.channel_id,
        as_user=True,
        text=response_text,
    )

    return


def _parse_message(message: BotMention) -> Optional[Tuple[str, str]]:
    # Look for the text after the mention of the bot
    search = re.search(r".*\<\@.+\> (.*)", message.text)

    if not search and message.message_type == "app_mention":
        return None

    text = search.groups("0")[0] if search else message.text
    cleaned_text = text.lower().strip().strip(".")

    return _split_text(cleaned_text)


def _split_text(text: str) -> Tuple[str, str]:
    words = text.split()

    first_word = words.pop(0)

    return first_word, " ".join(words).strip()


def parse_raw_request(raw_request_form: dict) -> BotMention:
    logger.info("Parsing raw request: {}".format(json.dumps(raw_request_form)))
    if raw_request_form["event"].get("subtype") == "message_changed":
        return BotMention(
            team_id=raw_request_form["team_id"],
            channel_id=raw_request_form["event"]["channel"],
            user_id=raw_request_form["event"]["message"]["user"],
            text=raw_request_form["event"]["message"]["text"],
            message_type=raw_request_form["event"]["message"]["type"],
        )
    else:
        return BotMention(
            team_id=raw_request_form["team_id"],
            channel_id=raw_request_form["event"]["channel"],
            user_id=raw_request_form["event"]["user"],
            text=raw_request_form["event"]["text"],
            message_type=raw_request_form["event"]["type"],
        )
