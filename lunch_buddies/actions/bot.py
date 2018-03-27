import logging
import re

from lunch_buddies.actions.create_poll import get_choices_from_message_text, InvalidPollOption
from lunch_buddies.constants.help import CREATE_POLL as CREATE_POLL_HELP_TEXT, CLOSE_POLL as CLOSE_POLL_HELP_TEXT, APP_EXPLANATION
from lunch_buddies.constants.queues import POLLS_TO_START, PollsToStartMessage, POLLS_TO_CLOSE, PollsToCloseMessage


logger = logging.getLogger(__name__)


def bot(message, slack_client, sqs_client, polls_dao, poll_responses_dao, teams_dao):
    text = _parse_text(message.text).lower().strip()
    logger.info('Handling message: {}'.format(text))

    if text.startswith('create'):
        rest_of_command = text.lstrip('create')
        logger.info('Rest of command: {}'.format(rest_of_command))
        response_text = _create(message, rest_of_command, sqs_client)
    elif text.startswith('close'):
        rest_of_command = text.lstrip('close')
        logger.info('Rest of command: {}'.format(rest_of_command))
        response_text = _close(message, rest_of_command, sqs_client)
    elif text.startswith('help'):
        response_text = APP_EXPLANATION
    else:
        return

    team = teams_dao.read('team_id', message.team_id)[0]
    slack_client.post_message(
        team=team,
        channel=message.channel_id,
        as_user=True,
        text=response_text,
    )

    return


def _parse_text(text):
    return re.search('\<\@[0-9A-Z]+\> (.*)', text).groups(0)[0]


def _create(message, rest_of_command, sqs_client):
    if rest_of_command.strip() == 'help':
        return CREATE_POLL_HELP_TEXT

    try:
        get_choices_from_message_text(rest_of_command)
    except InvalidPollOption as e:
        return 'Failed: {}'.format(str(e))

    sqs_client.send_message(
        POLLS_TO_START,
        PollsToStartMessage(
            team_id=message.team_id,
            channel_id=message.channel_id,
            user_id=message.user_id,
            text=rest_of_command,
        ),
    )

    return 'ok!'


def _close(message, rest_of_command, sqs_client):
    if rest_of_command.strip() == 'help':
        return CLOSE_POLL_HELP_TEXT

    sqs_client.send_message(
        POLLS_TO_CLOSE,
        PollsToCloseMessage(
            team_id=message.team_id,
            channel_id=message.channel_id,
            user_id=message.user_id,
        )
    )

    return 'ok!'
