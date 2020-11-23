import pytest

from tests.fixtures import (
    dynamo_team,
    stripe_customer,
    dynamo_poll,
)
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.clients.slack import Channel, User


@pytest.fixture
def mocked_sqs_v2(mocker):
    mocker.patch.object(
        service_context.clients.sqs_v2,
        "send_messages",
        auto_spec=True,
        return_value=True,
    )


@pytest.fixture
def mocked_slack(mocker):
    mocker.patch.object(
        service_context.clients.slack,
        "post_message",
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        service_context.clients.slack,
        "post_message_if_channel_exists",
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        service_context.clients.slack,
        "_channels_list_internal",
        auto_spec=True,
        return_value=[
            Channel(name="lunch_buddies", channel_id="test_channel_id"),
            Channel(name="foo", channel_id="foo"),
        ],
    )

    mocker.patch.object(
        service_context.clients.slack,
        "conversations_members",
        auto_spec=True,
        return_value=["user_id_one", "user_id_two"],
    )

    mocker.patch.object(
        service_context.clients.slack,
        "get_user_info",
        auto_spec=True,
        return_value=User(
            name="Test Name", email="test@example.com", tz="America/Los_Angeles"
        ),
    )


@pytest.fixture
def mocked_team(mocker):
    mocker.patch.object(
        service_context.daos.teams,
        "_read_internal",
        auto_spec=True,
        return_value=[dynamo_team],
    )


@pytest.fixture
def mocked_stripe(mocker):
    mocker.patch.object(
        service_context.clients.stripe,
        "create_customer",
        auto_spec=True,
        return_value=stripe_customer,
    )


@pytest.fixture
def mocked_polls(mocker):
    poll_one = dynamo_poll.copy()
    poll_one["callback_id"] = "f0d101f9-9aaa-4899-85c8-aa0a2dbb0bbb"
    poll_one["created_at"] = 1522117903.551714  # make it earlier
    mocker.patch.object(
        service_context.daos.polls,
        "_read_internal",
        auto_spec=True,
        return_value=[poll_one, dynamo_poll],
    )
    mocker.patch.object(
        service_context.daos.polls,
        "mark_poll_closed",
        auto_spec=True,
        return_value=True,
    )
    mocker.patch.object(
        service_context.daos.polls,
        "_create_internal",
        auto_spec=True,
        return_value=True,
    )
