import pytest

from lunch_buddies.lib.service_context import service_context
from lunch_buddies.actions.tests.fixtures import poll_response, dynamo_poll_response


@pytest.mark.parametrize("model, dynamo", [(poll_response, dynamo_poll_response),])
def test_roundtrip_convert(model, dynamo):
    to_dynamo = service_context.daos.poll_responses.convert_to_dynamo(model)

    assert to_dynamo == dynamo

    from_dynamo = service_context.daos.poll_responses.convert_from_dynamo(to_dynamo)

    assert from_dynamo == model
