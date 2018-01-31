from itertools import groupby
import random

from lunch_buddies.constants.queues import GROUPS_TO_NOTIFY, GroupsToNotifyMessage


def close_poll(message, slack_client, sqs_client, polls_dao, poll_responses_dao):
    team_id = message.team_id
    poll = polls_dao.find_latest_by_team_id(team_id)

    poll_responses = poll_responses_dao.read('callback_id', str(poll.callback_id))

    # randomly group the responding users
    poll_responses_by_response = {
        response: list(items)
        for response, items in groupby(
            poll_responses,
            key=lambda item: item.response,
        )
        if 'yes' in response
    }
    for answer, messages in poll_responses_by_response.items():
        for group in get_groups(messages, 7, 5):
            user_ids = [poll_response.user_id for poll_response in group]
            sqs_client.send_message(
                GROUPS_TO_NOTIFY,
                GroupsToNotifyMessage(**{'team_id': team_id, 'user_ids': user_ids, 'response': answer}),
            )

    return True


def get_groups(elements, group_size, smallest_group):
    if len(elements) <= group_size:
        return [elements]

    elements_copy = elements.copy()
    leftover_count = len(elements_copy) % group_size
    if leftover_count:
        leftovers = []
        leftover_indices = random.sample(list(range(len(elements_copy))), leftover_count)
        for index in leftover_indices:
            leftovers.append(elements_copy[index])
        elements_copy = [
            item
            for index, item in enumerate(elements_copy)
            if index not in leftover_indices
        ]

    groups = [
        list(item)
        for item in zip(
            *[iter(sorted(iter(list(elements_copy)), key=lambda k: random.random()))] * group_size
        )
    ]

    if leftovers:
        if len(leftovers) >= smallest_group:
            groups.append(leftovers)
        else:
            index = 0
            while leftovers:
                groups[index].append(leftovers.pop())
                index = index + 1

    return groups
