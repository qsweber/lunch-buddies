import pytest
from dynamo_dao import DynamoObject

from lunch_buddies.models.teams import Team
from lunch_buddies.lib.service_context import service_context
from tests.fixtures import team


@pytest.mark.parametrize(
    "model, dynamo",
    [
        (
            team,
            {
                "team_id": "123",
                "access_token": "DEPRECATED",
                "name": "fake-team-name",
                "bot_access_token": "fake-bot-token",
                "created_at": 1585153363.983078,
                "feature_notify_in_channel": 1,
                "stripe_customer_id": "fake-stripe-customer-id",
                "invoicing_enabled": 1,
            },
        )
    ],
)
def test_roundtrip_convert(model: Team, dynamo: DynamoObject) -> None:
    to_dynamo = service_context.daos.teams.convert_to_dynamo(model)

    assert to_dynamo == dynamo

    from_dynamo = service_context.daos.teams.convert_from_dynamo(to_dynamo)

    assert from_dynamo == model
