from collections import defaultdict
import random

from lunch_buddies.constants.queues import GROUPS_TO_NOTIFY, GroupsToNotifyMessage


def close_poll(message, slack_client, sqs_client, polls_dao, poll_responses_dao):
    team_id = message.team_id
    poll = polls_dao.find_latest_by_team_id(team_id)

    poll_responses = poll_responses_dao.read('callback_id', str(poll.callback_id))

    poll_responses_by_response = _group_by_answer(poll_responses)

    for answer, messages in poll_responses_by_response.items():
        for group in get_groups(messages, 6, 5, 7):
            user_ids = [poll_response.user_id for poll_response in group]
            sqs_client.send_message(
                GROUPS_TO_NOTIFY,
                GroupsToNotifyMessage(**{'team_id': team_id, 'user_ids': user_ids, 'response': answer}),
            )

    return True


def _group_by_answer(poll_responses):
    poll_responses_by_response = defaultdict(list)
    for poll_response in poll_responses:
        if 'yes' in poll_response.response:
            poll_responses_by_response[poll_response.response].append(poll_response)

    return dict(poll_responses_by_response)


def get_groups(elements, group_size, min_group_size, max_group_size):
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
