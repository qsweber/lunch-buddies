from typing import Dict

from lunch_buddies.types import (
    QueueConfig,
    PollsToCloseMessage,
    PollsToStartMessage,
    UsersToPollMessage,
    GroupsToNotifyMessage,
)


POLLS_TO_START = 'polls_to_start'
USERS_TO_POLL = 'users_to_poll'
POLLS_TO_CLOSE = 'polls_to_close'
GROUPS_TO_NOTIFY = 'groups_to_notify'

QUEUES: Dict[str, QueueConfig] = {
    POLLS_TO_START: QueueConfig(
        url='https://us-west-2.queue.amazonaws.com/120356305272/polls_to_start',
        message_type=PollsToStartMessage,
        sns_trigger='arn:aws:sns:us-west-2:120356305272:polls_to_start_messages_visible',
    ),
    USERS_TO_POLL: QueueConfig(
        url='https://us-west-2.queue.amazonaws.com/120356305272/users_to_poll',
        message_type=UsersToPollMessage,
        sns_trigger='arn:aws:sns:us-west-2:120356305272:users_to_poll_messages_visible',
    ),
    POLLS_TO_CLOSE: QueueConfig(
        url='https://us-west-2.queue.amazonaws.com/120356305272/polls_to_close',
        message_type=PollsToCloseMessage,
        sns_trigger='arn:aws:sns:us-west-2:120356305272:polls_to_close_messages_visible',
    ),
    GROUPS_TO_NOTIFY: QueueConfig(
        url='https://us-west-2.queue.amazonaws.com/120356305272/groups_to_notify',
        message_type=GroupsToNotifyMessage,
        sns_trigger='arn:aws:sns:us-west-2:120356305272:groups_to_notify_messages_visible',
    ),
}
