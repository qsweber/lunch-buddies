import datetime
import logging

from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.types import ListenToPoll
from lunch_buddies.models.poll_responses import PollResponse

logger = logging.getLogger(__name__)


def listen_to_poll(
    request_form: ListenToPoll,
    polls_dao: PollsDao,
    poll_responses_dao: PollResponsesDao,
) -> dict:
    poll = polls_dao.find_by_callback_id_or_die(
        request_form.team_id, request_form.callback_id
    )

    choice = [
        choice for choice in poll.choices if choice.key == request_form.choice_key
    ][0]

    poll_response = PollResponse(
        callback_id=request_form.callback_id,
        user_id=request_form.user_id,
        created_at=datetime.datetime.fromtimestamp(request_form.action_ts),
        response=request_form.choice_key,
    )
    poll_responses_dao.create(poll_response)

    outgoing_payload = request_form.original_message
    outgoing_payload["attachments"].append(
        {
            "text": ":white_check_mark: Your answer of `{}` was received!".format(
                choice.display_text
            )
        }
    )

    return outgoing_payload
