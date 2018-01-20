import time

from lunch_buddies import constants


def poll_user(request_payload, slack_client, polls_dao):
    callback_id = request_payload['callback_id']
    user_id = request_payload['user_id']

    poll = polls_dao.find_by_callback_id(callback_id)

    if not poll:
        raise Exception('poll not found')

    if poll.state != constants.CREATED:
        return

    time.sleep(1)

    slack_client.post_message(
        channel=user_id,
        text='Are you able to participate in Lunch Buddies today?',
        attachments=[
            {
                'text': 'Are you able to participate in Lunch Buddies today?',
                'fallback': 'Something has gone wrong.',
                'callback_id': callback_id,
                'color': '#3AA3E3',
                'attachment_type': 'default',
                'actions': [
                    {'name': 'answer', 'text': value, 'type': 'button', 'value': key}
                    for key, value in constants.CHOICES.items()
                ],
            },
        ]
    )

    return True
