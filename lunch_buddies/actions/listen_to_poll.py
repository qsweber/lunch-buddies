import datetime
import os

from lunch_buddies.dao import messages as messages_dao
from lunch_buddies.models.messages import Message


def listen_to_poll(request_payload):
    '''
    Things to test:
      - mock out the dao
      - request_payload should result in two calls to the dao
    '''
    incoming_message = Message(
        team_id=request_payload['team']['id'],
        channel_id=request_payload['channel']['id'],
        message_ts=request_payload['action_ts'],
        from_user_id=request_payload['user']['id'],
        to_user_id=os.environ['BOT_USER_ID'],
        type='POLL_RESPONSE',
        raw=request_payload,
    )
    messages_dao.create(incoming_message)

    outgoing_message_payload = request_payload['original_message'].copy()
    answer = request_payload['actions'][0]
    outgoing_message_payload['attachments'][0]['text'] = ':white_check_mark: You\'re answer of `{}` was received!'.format(
        [
            option['text']
            for option in request_payload['original_message']['attachments'][0]['actions']
            if option['value'] == answer['value']
        ][0]
    )
    outgoing_message_payload['attachments'][0]['actions'] = []

    outgoing_message = Message(
        team_id=incoming_message.team_id,
        channel_id=incoming_message.channel_id,
        message_ts=datetime.datetime.now().timestamp(),
        from_user_id=incoming_message.to_user_id,
        to_user_id=incoming_message.from_user_id,
        type='POLL_RESPONSE',
        raw=outgoing_message_payload,
    )
    messages_dao.create(outgoing_message)

    return outgoing_message_payload
