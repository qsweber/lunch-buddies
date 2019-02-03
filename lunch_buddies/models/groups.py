from typing import List, NamedTuple
from uuid import UUID


class Group(NamedTuple):
    callback_id: UUID
    user_ids: List[str]
    response_key: str
