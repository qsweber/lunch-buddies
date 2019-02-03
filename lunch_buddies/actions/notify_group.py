import random

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.groups import GroupsDao
from lunch_buddies.models.groups import Group
from lunch_buddies.types import GroupsToNotifyMessage


def notify_group(
    message: GroupsToNotifyMessage,
    slack_client: SlackClient,
    polls_dao: PollsDao,
    teams_dao: TeamsDao,
    groups_dao: GroupsDao,
) -> None:
    team = teams_dao.read('team_id', message.team_id)[0]
    poll = polls_dao.find_by_callback_id(message.team_id, message.callback_id)
    choice = [
        choice
        for choice in poll.choices
        if choice.key == message.response
    ][0]

    user_in_charge = random.choice(message.user_ids)
    text = (
        'Hello! This is your lunch group for today. ' +
        'You all should meet somewhere at `{}`. '.format(choice.time) +
        'I am selecting <@{}> to be in charge of picking the location.'.format(user_in_charge)
    )

    conversation = slack_client.open_conversation(
        team=team,
        users=','.join(message.user_ids),
    )

    group = Group(
        callback_id=message.callback_id,
        user_ids=message.user_ids,
        response_key=message.response,
    )

    groups_dao.create(group)

    slack_client.post_message(
        team=team,
        channel=conversation['channel']['id'],
        as_user=True,
        text=text,
    )

    return
