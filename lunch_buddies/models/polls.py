from decimal import Decimal
from typing import NamedTuple

Poll = NamedTuple(
    'Poll',
    [
        ('team_id', str),
        ('created_at_ts', Decimal),
        ('created_by_user_id', str),
        ('callback_id', str),
        ('state', str),          # [STARTED, DONE]
        ('raw', dict),
    ]
)
