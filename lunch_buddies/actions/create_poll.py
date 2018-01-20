from datetime import datetime
import uuid

from lunch_buddies import constants
from lunch_buddies.models.polls import Poll


def create_poll(request_payload, slack_client, sqs_client, polls_dao):
    team_id = request_payload['team_id']

    # TODO: make sure there is not already an active poll

    callback_id = uuid.uuid4()

    poll = Poll(
        team_id=team_id,
        created_at=datetime.now(),
        created_by_user_id=request_payload['user_id'],
        callback_id=callback_id,
        state=constants.CREATED,
        choices=constants.CHOICES,
    )

    polls_dao.create(poll)

    users_to_poll = [
        user
        for user in slack_client.list_users()
        if user['is_bot'] is False and user['name'] != 'slackbot'
    ]
    for user in users_to_poll:
        message = {'user_id': user['id'], 'callback_id': callback_id}
        sqs_client.send_message(constants.USERS_TO_POLL, message)

    return True
