import pytest
from dynamo_dao import DynamoObject

from lunch_buddies.models.groups import Group
from lunch_buddies.lib.service_context import service_context
from tests.fixtures import group


@pytest.mark.parametrize(
    "model, dynamo",
    [
        (
            group,
            {
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "user_ids": '["abc", "def"]',
                "response_key": "yes_1145",
            },
        )
    ],
)
def test_roundtrip_convert(model: Group, dynamo: DynamoObject) -> None:
    to_dynamo = service_context.daos.groups.convert_to_dynamo(model)

    assert to_dynamo == dynamo

    from_dynamo = service_context.daos.groups.convert_from_dynamo(to_dynamo)

    assert from_dynamo == model
