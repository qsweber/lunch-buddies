from typing import cast, List, NamedTuple

from lunch_buddies.actions.create_poll import parse_message_text, InvalidPollOption, InvalidPollSize
from lunch_buddies.lib.service_context import ServiceContext
from lunch_buddies.constants.help import CREATE_POLL
from lunch_buddies.constants.queues import PollsToStartMessage
from lunch_buddies.types import CreatePoll


def queue_create_poll(request_form: CreatePoll, service_context: ServiceContext) -> str:
    if _is_help(request_form):
        return CREATE_POLL

    try:
        _validate(request_form)
    except (InvalidPollOption, InvalidPollSize) as e:
        return 'Failed: {}'.format(str(e))

    message = PollsToStartMessage(
        team_id=request_form.team_id,
        channel_id=request_form.channel_id,
        user_id=request_form.user_id,
        text=request_form.text,
    )

    service_context.clients.sqs_v2.send_messages(
        'polls_to_start',
        cast(List[NamedTuple], [message]),
    )

    return 'ok!'


def _is_help(request_form: CreatePoll) -> bool:
    return request_form.text.lower().strip() == 'help'


def _validate(request_form: CreatePoll) -> bool:
    text = request_form.text

    parse_message_text(text)

    return True
