from typing import NamedTuple


POLLS_TO_START = 'polls_to_start'
USERS_TO_POLL = 'users_to_poll'
POLLS_TO_CLOSE = 'polls_to_close'
GROUPS_TO_NOTIFY = 'groups_to_notify'

PollsToStartMessage = NamedTuple(
    'PollsToStartMessage',
    [
        ('team_id', str),
        ('user_id', str),
    ],
)

UsersToPollMessage = NamedTuple(
    'UsersToPollMessage',
    [
        ('team_id', str),
        ('user_id', str),
        ('callback_id', str),
    ],
)

PollsToCloseMessage = NamedTuple('PollsToCloseMessage', [('team_id', str), ('user_id', str)])

GroupsToNotifyMessage = NamedTuple(
    'GroupsToNotifyMessage',
    [
        ('team_id', str),
        ('response', str),
        ('user_ids', list),
    ],
)

QUEUES = {
    POLLS_TO_START: {
        'url': 'https://us-west-2.queue.amazonaws.com/120356305272/polls_to_start',
        'type': PollsToStartMessage,
    },
    USERS_TO_POLL: {
        'url': 'https://us-west-2.queue.amazonaws.com/120356305272/users_to_poll',
        'type': UsersToPollMessage,
    },
    POLLS_TO_CLOSE: {
        'url': 'https://us-west-2.queue.amazonaws.com/120356305272/polls_to_close',
        'type': PollsToCloseMessage,
    },
    GROUPS_TO_NOTIFY: {
        'url': 'https://us-west-2.queue.amazonaws.com/120356305272/groups_to_notify',
        'type': GroupsToNotifyMessage,
    },
}
