from lunch_buddies.dao.base import Dao
from lunch_buddies.models.team_settings import TeamSettings
from lunch_buddies.clients.dynamo import DynamoClient, DynamoObject


class TeamSettingsDao(Dao[TeamSettings]):
    def __init__(self, dynamo: DynamoClient):
        super(TeamSettingsDao, self).__init__(dynamo, 'lunch_buddies_TeamSettings')

    def convert_to_dynamo(self, input: TeamSettings) -> DynamoObject:
        return {
            'team_id': input.team_id,
            'feature_notify_in_channel': int(input.feature_notify_in_channel),
        }

    def convert_from_dynamo(self, input: DynamoObject) -> TeamSettings:
        return TeamSettings(
            team_id=str(input['team_id']),
            feature_notify_in_channel=bool(input['feature_notify_in_channel']),
        )
