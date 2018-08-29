from collections import defaultdict
import random
from typing import Dict, List

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.constants.polls import CREATED
from lunch_buddies.constants.slack import LUNCH_BUDDIES_CHANNEL_NAME
from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.dao.poll_responses import PollResponsesDao
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.poll_responses import PollResponse
from lunch_buddies.models.polls import Poll, Choice
from lunch_buddies.models.teams import Team
from lunch_buddies.types import GroupsToNotifyMessage, PollsToCloseMessage


def close_poll(
    message: PollsToCloseMessage,
    slack_client: SlackClient,
    polls_dao: PollsDao,
    poll_responses_dao: PollResponsesDao,
    teams_dao: TeamsDao,
) -> List[GroupsToNotifyMessage]:
    team: Team = teams_dao.read('team_id', message.team_id)[0]
    channel_id = message.channel_id
    if not channel_id:
        lunch_buddies_channel = slack_client.get_channel(team, LUNCH_BUDDIES_CHANNEL_NAME)
        channel_id = lunch_buddies_channel['id']

    poll: Poll = polls_dao.find_latest_by_team_channel(message.team_id, channel_id)

    if not poll:
        # TODO: give the use some more information since they probably just need to find the right poll to close
        slack_client.post_message(
            team=team,
            channel=message.user_id,
            as_user=True,
            text='No poll found',
        )

        return []

    if poll.state != CREATED:
        slack_client.post_message(
            team=team,
            channel=message.user_id,
            as_user=True,
            text='The poll you tried to close has already been closed',
        )

        return []

    poll_responses: List[PollResponse] = poll_responses_dao.read('callback_id', str(poll.callback_id))

    poll_responses_by_choice = _group_by_answer(poll_responses, poll)

    messages_to_send = [
        GroupsToNotifyMessage(
            team_id=message.team_id,
            callback_id=poll.callback_id,
            user_ids=[poll_response.user_id for poll_response in group],
            response=choice.key,
        )
        for choice, poll_responses_for_choice in poll_responses_by_choice.items()
        for group in get_groups(poll_responses_for_choice, poll.group_size, max(1, poll.group_size - 1), 7)
    ]

    # Close right before notifying groups to keep this as atomic as possible with Dynamo
    polls_dao.mark_poll_closed(poll=poll)

    return messages_to_send


def _group_by_answer(poll_responses: List[PollResponse], poll: Poll) -> Dict[Choice, List[PollResponse]]:
    poll_responses_by_choice: Dict[Choice, List[PollResponse]] = defaultdict(list)
    for poll_response in poll_responses:
        choice = _get_choice_from_response(poll_response, poll)
        if choice.is_yes:
            poll_responses_by_choice[choice].append(poll_response)

    return poll_responses_by_choice


def _get_choice_from_response(poll_response: PollResponse, poll: Poll) -> Choice:
    return [
        choice
        for choice in poll.choices
        if choice.key == poll_response.response
    ][0]


def get_groups(elements: List[PollResponse], group_size: int, min_group_size: int, max_group_size: int) -> List[List[PollResponse]]:
    if len(elements) <= group_size:
        return [elements]

    elements_copy = elements.copy()
    random.shuffle(elements_copy)

    groups = [elements_copy[i:i + group_size] for i in range(0, len(elements_copy), group_size)]

    if len(groups[-1]) < min_group_size:
        last_group = groups.pop()

        if (max_group_size - group_size) * len(groups) >= len(last_group):
            # evenly distribute
            i = 0
            while last_group:
                groups[i].append(last_group.pop())
                if i > (len(groups) - 1):
                    i = 0
                else:
                    i = i + 1
        else:
            # try with a smaller group size
            return get_groups(elements, group_size - 1, min(group_size - 1, min_group_size), max_group_size)

    return groups
