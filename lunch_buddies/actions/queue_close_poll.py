from typing import cast, List, NamedTuple

from lunch_buddies.lib.service_context import ServiceContext
from lunch_buddies.constants.help import CLOSE_POLL
from lunch_buddies.types import ClosePoll, PollsToCloseMessage


def queue_close_poll(request_form: ClosePoll, service_contect: ServiceContext) -> str:
    if _is_help(request_form):
        return CLOSE_POLL

    message = PollsToCloseMessage(
        team_id=request_form.team_id,
        channel_id=request_form.channel_id,
        user_id=request_form.user_id,
    )

    service_contect.clients.sqs_v2.send_messages(
        'polls_to_close',
        cast(List[NamedTuple], [message]),
    )

    return 'ok!'


def _is_help(request_form: ClosePoll) -> bool:
    return request_form.text.lower().strip() == 'help'
