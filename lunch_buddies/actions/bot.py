import logging
import re
from typing import Optional, Tuple

from lunch_buddies.actions.queue_create_poll import queue_create_poll
from lunch_buddies.actions.queue_close_poll import queue_close_poll
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants.help import APP_EXPLANATION
from lunch_buddies.types import BotMention, ClosePoll, CreatePoll


logger = logging.getLogger(__name__)


def bot(
    message: BotMention,
    sqs_client: SqsClient,
) -> str:
    parsed_text = _parse_text(message.text)

    if not parsed_text:
        return ''

    first_word, rest_of_command = parsed_text
    logger.info('First word: {}, Rest of command: {}'.format(
        first_word,
        rest_of_command,
    ))

    if first_word == 'create':
        return queue_create_poll(
            CreatePoll(
                text=rest_of_command,
                team_id=message.team_id,
                channel_id=message.channel_id,
                user_id=message.user_id,
            ),
            sqs_client,
        )

    if first_word == 'close':
        return queue_close_poll(
            ClosePoll(
                team_id=message.team_id,
                channel_id=message.channel_id,
                user_id=message.user_id,
                text=rest_of_command,
            ),
            sqs_client,
        )
    elif first_word == 'help':
        return APP_EXPLANATION
    else:
        return ''


def _parse_text(text: str) -> Optional[Tuple[str, str]]:
    search = re.search('\<\@[0-9A-Z]+\> (.*)', text)

    if search:
        return _split_text(search.groups('0')[0].lower().strip())
    else:
        return None


def _split_text(text: str) -> Tuple[str, str]:
    words = text.split()

    first_word = words.pop(0)

    return first_word, ' '.join(words).strip()
