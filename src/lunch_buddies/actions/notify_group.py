import random

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.dao.groups import GroupsDao
from lunch_buddies.models.groups import Group
from lunch_buddies.models.teams import Team
from lunch_buddies.models.polls import Poll, Choice
from lunch_buddies.types import GroupsToNotifyMessage


def notify_group(
    message: GroupsToNotifyMessage,
    slack_client: SlackClient,
    polls_dao: PollsDao,
    teams_dao: TeamsDao,
    groups_dao: GroupsDao,
) -> None:
    team = teams_dao.read_one_or_die("team_id", message.team_id)
    poll = polls_dao.find_by_callback_id_or_die(message.team_id, message.callback_id)

    choice = [choice for choice in poll.choices if choice.key == message.response][0]

    group = Group(
        callback_id=message.callback_id,
        user_ids=message.user_ids,
        response_key=message.response,
    )

    groups_dao.create(group)

    if team.feature_notify_in_channel:
        _notify_in_channel(message, slack_client, team, poll, choice)
    else:
        _notify_private_group(message, slack_client, team, choice)

    return


def _notify_private_group(
    message: GroupsToNotifyMessage,
    slack_client: SlackClient,
    team: Team,
    choice: Choice,
) -> None:
    user_in_charge = random.choice(message.user_ids)
    text = (
        "Hello! This is your group for today. "
        + "You all should meet somewhere at `{}`. ".format(choice.time)
        + "I am selecting <@{}> to be in charge of picking the location.".format(
            user_in_charge
        )
    )
    conversation = slack_client.open_conversation(
        bot_access_token=team.bot_access_token,
        users=",".join(message.user_ids),
    )
    slack_client.post_message(
        bot_access_token=team.bot_access_token,
        channel=conversation.channel_id,
        as_user=True,
        text=text,
    )


def _notify_in_channel(
    message: GroupsToNotifyMessage,
    slack_client: SlackClient,
    team: Team,
    poll: Poll,
    choice: Choice,
) -> None:
    users_formatted = ", ".join(
        ["<@{}>".format(user_id) for user_id in message.user_ids]
    )
    text = (
        "Hey {}!".format(users_formatted)
        + " This is your group for today."
        + " You all should meet somewhere at `{}`.".format(choice.time)
    )
    result = slack_client.post_message(
        bot_access_token=team.bot_access_token,
        channel=poll.channel_id,
        as_user=True,
        text=text,
    )
    text = "<@{}> should pick the location.".format(random.choice(message.user_ids))
    slack_client.post_message(
        bot_access_token=team.bot_access_token,
        channel=poll.channel_id,
        as_user=True,
        text=text,
        thread_ts=result.ts,
    )
