from datetime import datetime
import uuid

from lunch_buddies.constants import polls
from lunch_buddies.constants.queues import USERS_TO_POLL, UsersToPollMessage
from lunch_buddies.models.polls import Poll


def create_poll(message, slack_client, sqs_client, polls_dao, poll_responses_dao):
    team_id = message.team_id

    # TODO: make sure there is not already an active poll

    callback_id = _get_uuid()
    created_at = _get_created_at()

    poll = Poll(
        team_id=team_id,
        created_at=created_at,
        created_by_user_id=message.user_id,
        callback_id=callback_id,
        state=polls.CREATED,
        choices=polls.CHOICES,
    )

    polls_dao.create(poll)

    users_to_poll = [
        user
        for user in slack_client.list_users()
        if user['is_bot'] is False and user['name'] != 'slackbot'
    ]
    for user in users_to_poll:
        message = {'team_id': team_id, 'user_id': user['id'], 'callback_id': callback_id}
        sqs_client.send_message(
            USERS_TO_POLL,
            UsersToPollMessage(**message),
        )

    return True


def _get_uuid():
    return uuid.uuid4()


def _get_created_at():
    return datetime.now()
