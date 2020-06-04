from datetime import datetime
from typing import NamedTuple
from uuid import UUID

PollResponse = NamedTuple(
    "PollResponse",
    [
        ("callback_id", UUID),
        ("user_id", str),
        ("created_at", datetime),
        ("response", str),
    ],
)
