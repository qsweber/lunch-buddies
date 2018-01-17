import datetime
from decimal import Decimal
import uuid

from lunch_buddies.dao import polls as polls_dao
from lunch_buddies.dao import messages as messages_dao
from lunch_buddies.models.messages import Message
from lunch_buddies.models.polls import Poll


def create_poll(request_payload, slack_client):
    team_id = request_payload['team_id']

    # TODO: make sure there is not already an active poll

    callback_id = str(uuid.uuid4())

    poll = Poll(
        team_id=team_id,
        created_at_ts=datetime.datetime.now().timestamp(),  # round to 6 decimals
        created_by_user_id=request_payload['user_id'],
        callback_id=callback_id,
        state='CREATED',
        raw=request_payload,
    )

    polls_dao.create(poll)

    users = [
        user
        for user in slack_client.list_users()
        if user['is_bot'] is False and user['name'] != 'slackbot'
    ]
    for user in users:
        sent_message_payload = slack_client.post_message(
            channel=user['id'],
            text='Are you able to participate in Lunch Buddies today?',
            attachments=[
                {
                    'text': 'Are you able to participate in Lunch Buddies today?',
                    'fallback': 'Something has gone wrong.',
                    'callback_id': callback_id,
                    'color': '#3AA3E3',
                    'attachment_type': 'default',
                    'actions': [
                        {
                            'name': 'answer',
                            'text': 'Yes (11:45)',
                            'type': 'button',
                            'value': 'yes_0'
                        },
                        {
                            'name': 'answer',
                            'text': 'Yes (12:30)',
                            'type': 'button',
                            'value': 'yes_1'
                        },
                        {
                            'name': 'answer',
                            'text': 'No',
                            'type': 'button',
                            'value': 'no'
                        },
                    ],
                },
            ]
        )

        sent_message = Message(
            team_id=team_id,
            channel_id=sent_message_payload['channel'],
            message_ts=Decimal(sent_message_payload['ts']),
            from_user_id=sent_message_payload['message']['bot_id'],
            to_user_id=user['id'],
            type='POLL_USER',
            raw=sent_message_payload,
        )

        messages_dao.create(sent_message)

    return {'text': 'Polled {} users.'.format(len(users))}
