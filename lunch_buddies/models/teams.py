from datetime import datetime
from typing import NamedTuple

Team = NamedTuple(
    'Team',
    [
        ('team_id', str),
        ('access_token', str),
        ('bot_access_token', str),
        ('created_at', datetime),
    ]
)
