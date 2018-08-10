from datetime import datetime
from typing import NamedTuple
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


class ChoiceList(list):
    pass


Poll = NamedTuple(
    'Poll',
    [
        ('team_id', str),
        ('created_at', datetime),  # TODO check for uniqueness upon creating
        ('channel_id', str),
        ('created_by_user_id', str),
        ('callback_id', UUID),
        ('state', str),
        ('choices', ChoiceList),
        ('group_size', int),
    ]
)
