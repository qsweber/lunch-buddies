import json
from uuid import UUID

from dynamo_dao import Dao, DynamoObject

from lunch_buddies.models.groups import Group


class GroupsDao(Dao[Group]):
    table_name = "lunch_buddies_Group"
    unique_key = ["callback_id", "user_ids"]

    def convert_to_dynamo(self, q: Group) -> DynamoObject:
        return {
            "callback_id": str(q.callback_id),
            "user_ids": json.dumps(q.user_ids),
            "response_key": q.response_key,
        }

    def convert_from_dynamo(self, q: DynamoObject) -> Group:
        return Group(
            callback_id=UUID(str(q["callback_id"])),
            user_ids=json.loads(str(q["user_ids"])),
            response_key=str(q["response_key"]),
        )
