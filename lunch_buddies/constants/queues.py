from typing import Any, NamedTuple

from lunch_buddies.types import (
    PollsToCloseMessage,
    PollsToStartMessage,
    UsersToPollMessage,
    GroupsToNotifyMessage,
)


class Queue(NamedTuple):
    queue_name: str
    message_type: Any


POLLS_TO_START = Queue('polls_to_start', PollsToStartMessage)
USERS_TO_POLL = Queue('users_to_poll', UsersToPollMessage)
POLLS_TO_CLOSE = Queue('polls_to_close', PollsToCloseMessage)
GROUPS_TO_NOTIFY = Queue('groups_to_notify', GroupsToNotifyMessage)
ERROR_QUEUE = Queue('error', '')

QUEUES = [
    POLLS_TO_START,
    USERS_TO_POLL,
    POLLS_TO_CLOSE,
    GROUPS_TO_NOTIFY,
]
