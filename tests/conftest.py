from datetime import datetime
from uuid import UUID

import pytest

from tests.fixtures import (
    team,
    stripe_customer,
    poll,
    poll_response,
)
from lunch_buddies.models.polls import Poll
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
        "read_one",
        auto_spec=True,
        return_value=team,
    )
    mocker.patch.object(
        service_context.daos.teams,
        "read_one_or_die",
        auto_spec=True,
        return_value=team,
    )
    mocker.patch.object(
        service_context.daos.teams,
        "read",
        auto_spec=True,
        return_value=[team],
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
    poll_one = Poll(
        team_id=poll.team_id,
        created_at=datetime.fromtimestamp(float(1522117903.551714)),  # make it earlier
        channel_id=poll.channel_id,
        created_by_user_id=poll.created_by_user_id,
        callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0bbb"),
        state=poll.state,
        choices=poll.choices,
        group_size=poll.group_size,
        stripe_invoice_id=poll.stripe_invoice_id,
    )
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[poll_one, poll],
    )
    mocker.patch.object(
        service_context.daos.polls,
        "mark_poll_closed",
        auto_spec=True,
        return_value=True,
    )
    mocker.patch.object(
        service_context.daos.polls,
        "create",
        auto_spec=True,
        return_value=True,
    )


@pytest.fixture
def mocked_poll_responses(mocker):
    mocker.patch.object(
        service_context.daos.poll_responses,
        "read",
        auto_spec=True,
        return_value=[
            poll_response,
            poll_response._replace(user_id="user_id_two"),
        ],
    )
