from decimal import Decimal
from uuid import UUID

from lunch_buddies.dao.base import Dao
from lunch_buddies.models.poll_responses import PollResponse
from lunch_buddies.clients.dynamo import DynamoClient, DynamoObject


class PollResponsesDao(Dao[PollResponse]):
    def __init__(self, dynamo: DynamoClient):
        super(PollResponsesDao, self).__init__(dynamo, 'lunch_buddies_PollResponse')

    def convert_to_dynamo(self, q: PollResponse) -> DynamoObject:
        return {
            'callback_id': str(q.callback_id),
            'user_id': q.user_id,
            'created_at': Decimal(q.created_at.timestamp()),
            'response': q.response,
        }

    def convert_from_dynamo(self, q: DynamoObject) -> PollResponse:
        return PollResponse(
            callback_id=UUID(str(q['callback_id'])),
            user_id=str(q['user_id']),
            created_at=self._convert_datetime_from_dynamo(q['created_at']),
            response=str(q['response']),
        )
