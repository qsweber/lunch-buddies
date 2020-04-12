from datetime import datetime
from typing import NamedTuple


class Team(NamedTuple):
    team_id: str
    access_token: str
    bot_access_token: str
    name: str
    created_at: datetime
