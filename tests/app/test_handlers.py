from pytest_mock import MockerFixture

import lunch_buddies.app.handlers as module
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.types import PollsToStartMessage
from tests.app.requests.sqs_message import test_input, test_output  # type: ignore


def test_sqs_handler(mocker: MockerFixture) -> None:
    mocker.patch.object(module, "create_poll_action", auto_spec=True, return_value=[])

    module.create_poll_from_queue(test_input)

    module.create_poll_action.assert_called_with(  # type: ignore
        PollsToStartMessage(team_id="1", channel_id="2", user_id="abc", text="def"),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )


def test_sqs_handler_failure(mocker: MockerFixture) -> None:
    mocker.patch.object(
        service_context.clients.sqs_v2,
        "set_visibility_timeout_with_backoff",
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        module,
        "create_poll_action",
        auto_spec=True,
        side_effect=Exception("test failure message"),
    )

    try:
        module.create_poll_from_queue(test_input)
        assert 1 != 1
    except Exception as err:
        assert err.args[0] == "test failure message"

    service_context.clients.sqs_v2.set_visibility_timeout_with_backoff.assert_called_once()  # type: ignore
    service_context.clients.sqs_v2.set_visibility_timeout_with_backoff.assert_called_with(  # type: ignore
        test_output[0]
    )
