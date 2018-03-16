import time

from lunch_buddies.constants.polls import CREATED


def poll_user(message, slack_client, sqs_client, polls_dao, poll_responses_dao, teams_dao):
    team_id = message.team_id
    team = teams_dao.read('team_id', team_id)[0]

    callback_id = message.callback_id
    user_id = message.user_id

    poll = polls_dao.find_by_callback_id(team_id, callback_id)

    if not poll:
        raise Exception('poll not found')

    if poll.state != CREATED:
        return

    time.sleep(1)

    slack_client.post_message(
        team=team,
        channel=user_id,
        as_user=True,
        text='Are you able to participate in Lunch Buddies today?',
        attachments=[
            {
                'fallback': 'Something has gone wrong.',
                'callback_id': str(callback_id),
                'color': '#3AA3E3',
                'attachment_type': 'default',
                'actions': [
                    {'name': 'answer', 'text': choice.display_text, 'type': 'button', 'value': choice.key}
                    for choice in poll.choices
                ],
            },
        ]
    )

    return True
