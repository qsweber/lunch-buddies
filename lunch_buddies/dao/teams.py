from decimal import Decimal
from datetime import datetime

from lunch_buddies.dao.base import Dao
from lunch_buddies.models.teams import Team
from lunch_buddies.clients.dynamo import DynamoClient, DynamoObject


class TeamsDao(Dao[Team]):
    def __init__(self, dynamo: DynamoClient):
        super(TeamsDao, self).__init__(dynamo, 'lunch_buddies_Team')

    def convert_to_dynamo(self, input: Team) -> DynamoObject:
        return {
            'team_id': input.team_id,
            'access_token': input.access_token,
            'bot_access_token': input.bot_access_token,
            'name': input.name,
            'created_at': Decimal(input.created_at.timestamp())
        }

    def convert_from_dynamo(self, input: DynamoObject) -> Team:
        return Team(
            team_id=str(input['team_id']),
            access_token=str(input['access_token']),
            bot_access_token=str(input['bot_access_token']),
            name=str(input['name']),
            created_at=datetime.fromtimestamp(float(input['created_at'])),
        )
