import pytest
from dynamo_dao import DynamoObject

from lunch_buddies.models.poll_responses import PollResponse
from lunch_buddies.lib.service_context import service_context
from tests.fixtures import poll_response


@pytest.mark.parametrize(
    "model, dynamo",
    [
        (
            poll_response,
            {
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "user_id": "user_id_one",
                "created_at": 1522117983.551714,
                "response": "yes_1130",
            },
        )
    ],
)
def test_roundtrip_convert(model: PollResponse, dynamo: DynamoObject) -> None:
    to_dynamo = service_context.daos.poll_responses.convert_to_dynamo(model)

    assert to_dynamo == dynamo

    from_dynamo = service_context.daos.poll_responses.convert_from_dynamo(to_dynamo)

    assert from_dynamo == model
