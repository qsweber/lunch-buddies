import pytest

from lunch_buddies.lib.service_context import service_context
from lunch_buddies.actions.tests.fixtures import team_settings, dynamo_team_settings


@pytest.mark.parametrize(
    'model, dynamo',
    [
        (team_settings, dynamo_team_settings),
    ]
)
def test_roundtrip_convert(model, dynamo):
    to_dynamo = service_context.daos.team_settings.convert_to_dynamo(model)

    assert to_dynamo == dynamo

    from_dynamo = service_context.daos.team_settings.convert_from_dynamo(to_dynamo)

    assert from_dynamo == model
