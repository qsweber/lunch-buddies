import time

from lunch_buddies import constants


def poll_user(message, slack_client, sqs_client, polls_dao, poll_responses_dao):
    team_id = message.team_id
    callback_id = message.callback_id
    user_id = message.user_id

    poll = polls_dao.find_by_callback_id(team_id, callback_id)

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
                'callback_id': str(callback_id),
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