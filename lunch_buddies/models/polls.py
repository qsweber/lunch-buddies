from datetime import datetime
from typing import NamedTuple, List
from uuid import UUID


Choice = NamedTuple(
    'Choice',
    [
        ('key', str),
        ('is_yes', bool),
        ('time', str),
        ('display_text', str),
    ]
)

Poll = NamedTuple(
    'Poll',
    [
        ('team_id', str),
        ('created_at', datetime),  # TODO check for uniqueness upon creating
        ('channel_id', str),
        ('created_by_user_id', str),
        ('callback_id', UUID),
        ('state', str),
        ('choices', List[Choice]),
        ('group_size', int),
    ]
)
