import datetime
import logging
from uuid import UUID

from lunch_buddies.models.poll_responses import PollResponse

logger = logging.getLogger(__name__)


def listen_to_poll(request_form, polls_dao, poll_responses_dao):
    callback_id = UUID(request_form['callback_id'])
    team_id = request_form['team']['id']
    response = request_form['actions'][0]['value']
    poll_response = PollResponse(
        callback_id=callback_id,
        user_id=request_form['user']['id'],
        created_at=datetime.datetime.fromtimestamp(float(request_form['action_ts'])),
        response=response,
    )
    poll_responses_dao.create(poll_response)
    poll = polls_dao.find_by_callback_id(team_id, callback_id)

    outgoing_message_payload = request_form['original_message'].copy()
    outgoing_message_payload['attachments'].append({
        'text': ':white_check_mark: Your answer of `{}` was received!'.format(dict(poll.choices)[response])
    })

    return outgoing_message_payload
