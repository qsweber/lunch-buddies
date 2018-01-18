from itertools import groupby
import random

from lunch_buddies.dao import messages as messages_dao
from lunch_buddies.dao import polls as polls_dao
from lunch_buddies.models.messages import Message


def close_poll(request_payload, slack_client):
    # find the most recently created poll for this team
    team_id = slack_client.list_users()[0]['team_id']
    poll = polls_dao.read(team_id)[-1]

    # pull all of the messages that are a response to this poll
    answers = [
        message
        for message in messages_dao.read(team_id)
        if message.type == 'POLL_RESPONSE' and
        'callback_id' in message.raw and
        message.raw['callback_id'] == poll.callback_id
    ]

    # randomly group the responding users
    answers_by_answer = {
        answer: list(messages)
        for answer, messages in groupby(
            answers,
            key=lambda item: item.raw['actions'][0]['value']
        )
    }

    groups_count = 0
    users_count = 0
    for answer, messages in answers_by_answer.items():
        if 'yes' in answer:
            groups = get_groups(messages, 7, 5)

            for group in groups:
                hourminute = answer.split('_')[1]
                hourminute_formatted = '{}:{}'.format(hourminute[0:2], hourminute[2:4])

                user_in_charge = random.choice(group)
                text = (
                    'Hello! This is your lunch group for today. ' +
                    'You all should meet somewhere at `{}`. '.format(hourminute_formatted) +
                    'I am selecting <@{}> to be in charge of picking the location.'.format(user_in_charge.from_user_id)
                )

                conversation = slack_client.open_conversation(users=','.join([user.from_user_id for user in group]))

                outgoing_message_payload = slack_client.post_message(
                    channel=conversation['channel']['id'],
                    text=text,
                )

                outgoing_message = Message(
                    team_id=team_id,
                    channel_id=conversation['channel']['id'],
                    message_ts=outgoing_message_payload['ts'],
                    from_user_id=outgoing_message_payload['message']['bot_id'],
                    to_user_id=','.join([user.from_user_id for user in group]),
                    type='POLL_RESULTS',
                    raw=outgoing_message_payload,
                )

                messages_dao.create(outgoing_message)

                groups_count = groups_count + 1
                users_count = users_count + len(group)

    return {'text': 'Sent messages to {} groups ({} users)'.format(
        groups_count,
        users_count,
    )}


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
