from datetime import datetime
from uuid import UUID

from pytest_mock import MockerFixture

from lunch_buddies.models.poll_responses import PollResponse
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.types import ListenToPoll
import lunch_buddies.actions.listen_to_poll as module


def test_listen_to_poll(mocker: MockerFixture, mocked_polls: MockerFixture) -> None:
    original_message = {
        "text": "Are you able to participate in Lunch Buddies today?",
        "username": "Lunch Buddies",
        "bot_id": "fake_bot_id",
        "attachments": [
            {
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "fallback": "Something has gone wrong.",
                "id": 1,
                "color": "3AA3E3",
                "actions": [
                    {
                        "id": "1",
                        "name": "answer",
                        "text": "Yes (11:30)",
                        "type": "button",
                        "value": "yes_1130",
                        "style": "",
                    },
                    {
                        "id": "1",
                        "name": "answer",
                        "text": "Yes (12:30)",
                        "type": "button",
                        "value": "yes_1230",
                        "style": "",
                    },
                    {
                        "id": "2",
                        "name": "answer",
                        "text": "No",
                        "type": "button",
                        "value": "no",
                        "style": "",
                    },
                ],
            }
        ],
        "type": "message",
        "subtype": "bot_message",
        "ts": "1516117976.000223",
    }

    mocker.patch.object(
        service_context.daos.poll_responses,
        "create",
        autospec=True,
        return_value=True,
    )

    outgoing_message = module.listen_to_poll(
        ListenToPoll(
            original_message=original_message,
            team_id="fake_team_id",
            user_id="fake_user_id",
            choice_key="yes_1130",
            action_ts=float("1516117984.234873"),
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
        ),
        service_context.daos.polls,
        service_context.daos.poll_responses,
    )

    expected_poll_response = PollResponse(
        callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
        user_id="fake_user_id",
        created_at=datetime.fromtimestamp(1516117984.234873),
        response="yes_1130",
    )

    service_context.daos.poll_responses.create.assert_called_with(  # type: ignore
        expected_poll_response
    )

    expected_outgoing_message = {
        "text": "Are you able to participate in Lunch Buddies today?",
        "username": "Lunch Buddies",
        "bot_id": "fake_bot_id",
        "attachments": [
            {
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "fallback": "Something has gone wrong.",
                "id": 1,
                "color": "3AA3E3",
                "actions": [
                    {
                        "id": "1",
                        "name": "answer",
                        "text": "Yes (11:30)",
                        "type": "button",
                        "value": "yes_1130",
                        "style": "",
                    },
                    {
                        "id": "1",
                        "name": "answer",
                        "text": "Yes (12:30)",
                        "type": "button",
                        "value": "yes_1230",
                        "style": "",
                    },
                    {
                        "id": "2",
                        "name": "answer",
                        "text": "No",
                        "type": "button",
                        "value": "no",
                        "style": "",
                    },
                ],
            },
            {"text": ":white_check_mark: Your answer of `Yes (11:30)` was received!"},
        ],
        "type": "message",
        "subtype": "bot_message",
        "ts": "1516117976.000223",
    }

    assert outgoing_message == expected_outgoing_message
