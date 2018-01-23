from typing import NamedTuple

POLLS_TO_START = 'polls_to_start'
USERS_TO_POLL = 'users_to_poll'
POLLS_TO_CLOSE = 'polls_to_close'
GROUPS_TO_NOTIFY = 'groups_to_notify'

SQS_QUEUES = [
    POLLS_TO_START,
    USERS_TO_POLL,
    POLLS_TO_CLOSE,
    GROUPS_TO_NOTIFY,
]

SQS_QUEUE_URLS = {
    POLLS_TO_START: 'https://us-west-2.queue.amazonaws.com/120356305272/polls_to_start',
    USERS_TO_POLL: 'https://us-west-2.queue.amazonaws.com/120356305272/users_to_poll',
    POLLS_TO_CLOSE: 'https://us-west-2.queue.amazonaws.com/120356305272/polls_to_close',
    GROUPS_TO_NOTIFY: 'https://us-west-2.queue.amazonaws.com/120356305272/groups_to_notify',
}

SQS_QUEUE_INTERFACES = {
    POLLS_TO_START: NamedTuple(
        'Message',
        [
            ('team_id', str),
            ('user_id', str),
        ],
    ),
    USERS_TO_POLL: NamedTuple(
        'Message',
        [
            ('team_id', str),
            ('user_id', str),
            ('callback_id', str),
        ],
    ),
    POLLS_TO_CLOSE: NamedTuple('Message', [('team_id', str)]),
    GROUPS_TO_NOTIFY: NamedTuple(
        'Message',
        [
            ('team_id', str),
            ('response', str),
            ('user_ids', list),
        ],
    ),
}

CHOICES = {'yes_1145': 'Yes (11:45)', 'yes_1230': 'Yes (12:30)', 'no': 'No'}

CREATED = 'CREATED'
CLOSED = 'CLOSED'

POLL_STATES = [
    CREATED,
    CLOSED,
]
