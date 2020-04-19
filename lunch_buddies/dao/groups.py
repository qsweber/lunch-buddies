import json
from uuid import UUID

from lunch_buddies.dao.base import Dao
from lunch_buddies.models.groups import Group
from lunch_buddies.clients.dynamo import DynamoClient, DynamoObject


class GroupsDao(Dao[Group]):
    def __init__(self, dynamo: DynamoClient):
        super(GroupsDao, self).__init__(dynamo, 'lunch_buddies_Group', ['callback_id', 'user_ids'])

    def convert_to_dynamo(self, q: Group) -> DynamoObject:
        return {
            'callback_id': str(q.callback_id),
            'user_ids': json.dumps(q.user_ids),
            'response_key': q.response_key,
        }

    def convert_from_dynamo(self, q: DynamoObject) -> Group:
        return Group(
            callback_id=UUID(str(q['callback_id'])),
            user_ids=json.loads(str(q['user_ids'])),
            response_key=str(q['response_key']),
        )
