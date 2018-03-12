import datetime
import logging
from uuid import UUID

from lunch_buddies.models.poll_responses import PollResponse

logger = logging.getLogger(__name__)


def listen_to_poll(request_form, polls_dao, poll_responses_dao):
    callback_id, team_id, choice_key, action_ts, user_id, outgoing_message_payload = _parse_form(request_form)

    poll = polls_dao.find_by_callback_id(team_id, callback_id)

    choice = [choice for choice in poll.choices if choice.key == choice_key][0]

    poll_response = PollResponse(
        callback_id=callback_id,
        user_id=user_id,
        created_at=datetime.datetime.fromtimestamp(float(action_ts)),
        response=choice_key,
    )
    poll_responses_dao.create(poll_response)

    outgoing_message_payload['attachments'].append({
        'text': ':white_check_mark: Your answer of `{}` was received!'.format(choice.display_text)
    })

    return outgoing_message_payload


def _parse_form(request_form):
    callback_id = UUID(request_form['callback_id'])
    team_id = request_form['team']['id']
    choice_key = request_form['actions'][0]['value']
    action_ts = request_form['action_ts']
    user_id = request_form['user']['id']
    outgoing_message_payload = request_form['original_message'].copy()

    return callback_id, team_id, choice_key, action_ts, user_id, outgoing_message_payload
