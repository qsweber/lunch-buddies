import datetime
from uuid import UUID

from lunch_buddies.models.poll_responses import PollResponse


def listen_to_poll(request_payload, polls_dao, poll_responses_dao):
    callback_id = UUID(request_payload['callback_id'])
    response = request_payload['actions'][0]['value']
    poll_response = PollResponse(
        callback_id=callback_id,
        user_id=request_payload['user']['id'],
        created_at=datetime.datetime.fromtimestamp(request_payload['action_ts']),
        response=response,
    )
    poll_responses_dao.create(poll_response)
    poll = polls_dao.find_by_callback_id(callback_id)

    outgoing_message_payload = request_payload['original_message'].copy()
    outgoing_message_payload['attachments'] = [{
        'text': ':white_check_mark: You\'re answer of `{}` was received!'.format(poll.choices[response])
    }]

    return outgoing_message_payload
