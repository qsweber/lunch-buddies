import time

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.constants.polls import CREATED
from lunch_buddies.types import UsersToPollMessage


def poll_user(
    message: UsersToPollMessage,
    slack_client: SlackClient,
    polls_dao: PollsDao,
    teams_dao: TeamsDao,
) -> None:
    team_id = message.team_id
    team = teams_dao.read_one_or_die('team_id', team_id)

    callback_id = message.callback_id
    user_id = message.user_id

    poll = polls_dao.find_by_callback_id_or_die(team_id, callback_id)

    if poll.state != CREATED:
        return

    time.sleep(1)

    slack_client.post_message(
        bot_access_token=team.bot_access_token,
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

    return
