from datetime import datetime
from typing import NamedTuple
from uuid import UUID

Poll = NamedTuple(
    'Poll',
    [
        ('team_id', str),
        ('created_at', datetime),
        ('created_by_user_id', str),
        ('callback_id', UUID),
        ('state', str),
        ('choices', list),
    ]
)
