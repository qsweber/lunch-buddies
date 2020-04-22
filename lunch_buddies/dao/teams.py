from decimal import Decimal

from lunch_buddies.dao.base import Dao
from lunch_buddies.models.teams import Team
from lunch_buddies.clients.dynamo import DynamoClient, DynamoObject


class TeamsDao(Dao[Team]):
    def __init__(self, dynamo: DynamoClient):
        super(TeamsDao, self).__init__(dynamo, 'lunch_buddies_Team', ['team_id'])

    def convert_to_dynamo(self, input: Team) -> DynamoObject:
        return {
            'team_id': input.team_id,
            'access_token': input.access_token,
            'bot_access_token': input.bot_access_token,
            'name': input.name,
            'created_at': Decimal(input.created_at.timestamp()),
            'feature_notify_in_channel': 1 if input.feature_notify_in_channel else 0,
            'stripe_customer_id': input.stripe_customer_id if input.stripe_customer_id else None,
        }

    def convert_from_dynamo(self, input: DynamoObject) -> Team:
        return Team(
            team_id=str(input['team_id']),
            access_token=str(input['access_token']),
            bot_access_token=str(input['bot_access_token']),
            name=str(input['name']),
            created_at=self._convert_datetime_from_dynamo(input['created_at']),
            feature_notify_in_channel=bool(input['feature_notify_in_channel']) if 'feature_notify_in_channel' in input else False,
            stripe_customer_id=str(input['stripe_customer_id']) if 'stripe_customer_id' in input and input['stripe_customer_id'] is not None else None,
        )
