from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

Message = NamedTuple(
    'Message',
    [
        ('team_id', str),
        ('channel_id', str),
        ('message_ts', Decimal),
        ('from_user_id', str),
        ('to_user_id', str),
        ('received_at', datetime),
        ('type', str),
        ('raw', dict),
    ]
)
