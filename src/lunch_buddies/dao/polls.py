import json
from uuid import UUID
from typing import List, Optional

from dynamo_dao import Dao, DynamoObject

from lunch_buddies.lib.conversion_helpers import (
    convert_datetime_from_dynamo,
    convert_datetime_to_decimal,
)
from lunch_buddies.constants.polls import CLOSED
from lunch_buddies.models.polls import Poll, Choice


class PollsDao(Dao[Poll]):
    table_name = "lunch_buddies_Poll"
    unique_key = ["team_id", "created_at"]

    def find_by_callback_id_or_die(self, team_id: str, callback_id: UUID) -> Poll:
        polls_for_team = self.read("team_id", team_id)

        if not polls_for_team:
            raise Exception("no polls found for team {}".format(team_id))

        polls = [poll for poll in polls_for_team if poll.callback_id == callback_id]

        if len(polls) == 0:
            raise Exception(
                "poll not found with callback_id {}".format(str(callback_id))
            )
        elif len(polls) > 1:
            raise Exception(
                "more than one poll found with callback_id {}".format(str(callback_id))
            )

        return polls[0]

    def find_latest_by_team_channel(
        self, team_id: str, channel_id: Optional[str]
    ) -> Optional[Poll]:
        polls = self.read("team_id", team_id)

        if not polls:
            return None

        if channel_id:
            polls = [poll for poll in polls if poll.channel_id == channel_id]
            if not polls:
                return None

        return polls[-1]

    def mark_poll_closed(self, poll: Poll) -> None:
        self.update(poll, poll._replace(state=CLOSED))

    def mark_poll_invoiced(self, poll: Poll, stripe_invoice_id: str) -> None:
        self.update(poll, poll._replace(stripe_invoice_id=stripe_invoice_id))

    def convert_to_dynamo(self, q: Poll) -> DynamoObject:
        return {
            "team_id": q.team_id,
            "created_at": convert_datetime_to_decimal(q.created_at),
            "channel_id": q.channel_id if q.channel_id != "OLD_POLL" else None,
            "created_by_user_id": q.created_by_user_id,
            "callback_id": str(q.callback_id),
            "state": q.state,
            "choices": choices_to_dynamo(q.choices),
            "group_size": q.group_size,
            "stripe_invoice_id": q.stripe_invoice_id,
        }

    def convert_from_dynamo(self, q: DynamoObject) -> Poll:
        return Poll(
            team_id=str(q["team_id"]),
            created_at=convert_datetime_from_dynamo(q["created_at"]),
            channel_id=str(q["channel_id"])
            if "channel_id" in q and q["channel_id"] is not None
            else "OLD_POLL",
            created_by_user_id=str(q["created_by_user_id"]),
            callback_id=UUID(str(q["callback_id"])),
            state=str(q["state"]),
            choices=choices_from_dynamo(str(q["choices"])),
            group_size=int(str(q["group_size"])),
            stripe_invoice_id=str(q["stripe_invoice_id"])
            if "stripe_invoice_id" in q and q["stripe_invoice_id"] is not None
            else None,
        )


def choices_from_dynamo(value: str) -> List[Choice]:
    # TODO: remove below
    choices = json.loads(value)
    if isinstance(choices, dict):
        # version 1.0
        return [
            Choice(
                key=key,
                is_yes=("yes" in key),
                time="{}:{}".format(key[-4:-2], key[-2:]) if "yes" in key else "",
                display_text=display_text,
            )
            for key, display_text in choices.items()
        ]
    elif isinstance(choices, list):
        if len(choices[0]) == 2:
            # version 2.0
            return [
                Choice(
                    key=key,
                    is_yes=("yes" in key),
                    time=("{}:{}".format(key[-4:-2], key[-2:]) if "yes" in key else ""),
                    display_text=display_text,
                )
                for key, display_text in choices
            ]
    # TODO: remove above

    return [
        Choice(
            key=str(choice["key"]),
            is_yes=bool(choice["is_yes"]),
            time=choice["time"],
            display_text=str(choice["display_text"]),
        )
        for choice in json.loads(value)
    ]


def choices_to_dynamo(value: List[Choice]) -> str:
    return json.dumps([choice._asdict() for choice in value])
