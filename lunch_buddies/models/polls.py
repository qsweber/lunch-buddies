from datetime import datetime
from typing import NamedTuple, List, Optional
from uuid import UUID


class Choice(NamedTuple):
    key: str
    is_yes: bool
    time: str
    display_text: str


class Poll(NamedTuple):
    team_id: str
    created_at: datetime  # TODO check for uniqueness upon creating
    channel_id: Optional[str]
    created_by_user_id: str
    callback_id: UUID
    state: str
    choices: List[Choice]
    group_size: int
