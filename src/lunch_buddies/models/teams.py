from datetime import datetime
from typing import NamedTuple, Optional


class Team(NamedTuple):
    team_id: str
    access_token: str
    bot_access_token: str
    name: str
    created_at: datetime
    feature_notify_in_channel: bool
    invoicing_enabled: Optional[bool]
    stripe_customer_id: Optional[str]
