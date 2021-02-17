from uuid import UUID

from dynamo_dao import Dao, DynamoObject

from lunch_buddies.models.poll_responses import PollResponse
from lunch_buddies.lib.conversion_helpers import (
    convert_datetime_from_dynamo,
    convert_datetime_to_decimal,
)


class PollResponsesDao(Dao[PollResponse]):
    table_name = "lunch_buddies_PollResponse"
    unique_key = ["callback_id", "user_id"]

    def convert_to_dynamo(self, q: PollResponse) -> DynamoObject:
        return {
            "callback_id": str(q.callback_id),
            "user_id": q.user_id,
            "created_at": convert_datetime_to_decimal(q.created_at),
            "response": q.response,
        }

    def convert_from_dynamo(self, q: DynamoObject) -> PollResponse:
        return PollResponse(
            callback_id=UUID(str(q["callback_id"])),
            user_id=str(q["user_id"]),
            created_at=convert_datetime_from_dynamo(q["created_at"]),
            response=str(q["response"]),
        )
