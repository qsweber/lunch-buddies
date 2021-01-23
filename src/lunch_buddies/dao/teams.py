from dynamo_dao import Dao, DynamoObject

from lunch_buddies.models.teams import Team
from lunch_buddies.lib.conversion_helpers import (
    convert_datetime_from_dynamo,
    convert_datetime_to_decimal,
)


class TeamsDao(Dao[Team]):
    table_name = "lunch_buddies_Team"
    unique_key = ["team_id"]

    def convert_to_dynamo(self, var: Team) -> DynamoObject:
        return {
            "team_id": var.team_id,
            "access_token": var.access_token,
            "bot_access_token": var.bot_access_token,
            "name": var.name,
            "created_at": convert_datetime_to_decimal(var.created_at),
            "feature_notify_in_channel": 1 if var.feature_notify_in_channel else 0,
            "stripe_customer_id": var.stripe_customer_id
            if var.stripe_customer_id
            else None,
            "invoicing_enabled": 1 if var.invoicing_enabled else 0,
        }

    def convert_from_dynamo(self, var: DynamoObject) -> Team:
        return Team(
            team_id=str(var["team_id"]),
            access_token=str(var["access_token"]),
            bot_access_token=str(var["bot_access_token"]),
            name=str(var["name"]) if "name" in var else "",
            created_at=convert_datetime_from_dynamo(var["created_at"]),
            feature_notify_in_channel=bool(var["feature_notify_in_channel"])
            if "feature_notify_in_channel" in var
            else False,
            stripe_customer_id=str(var["stripe_customer_id"])
            if "stripe_customer_id" in var and var["stripe_customer_id"] is not None
            else None,
            invoicing_enabled=bool(var["invoicing_enabled"])
            if "invoicing_enabled" in var
            else False,
        )
