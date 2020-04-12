from datetime import datetime
from typing import NamedTuple, Optional


class Team(NamedTuple):
    team_id: str
    access_token: str
    bot_access_token: str
    name: str
    stripe_customer_id: Optional[str]
    created_at: datetime
