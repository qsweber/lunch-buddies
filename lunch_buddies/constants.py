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
    POLLS_TO_START: '',
    USERS_TO_POLL: '',
    POLLS_TO_CLOSE: '',
    GROUPS_TO_NOTIFY: '',
}

CHOICES = {'yes_1145': 'Yes (11:45)', 'yes_1230': 'Yes (12:30)', 'no': 'No'}

CREATED = 'CREATED'
CLOSED = 'CLOSED'

POLL_STATES = [
    CREATED,
    CLOSED,
]
