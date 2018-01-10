from typings import NamedTuple
from datetime import datetime

Message = NamedTuple(
    'Message',
    [
        ('team_id', str),
        ('channel_id', str),
        ('message_id', str), # not sure where we can get this
        ('from_user_id', str),
        ('to_user_id', str),
        ('received_at', datetime),
        ('type', str), # one of list
        ('text', str),

    ]
)
