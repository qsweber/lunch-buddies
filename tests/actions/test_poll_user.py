from uuid import UUID

from pytest_mock import MockerFixture

import lunch_buddies.actions.poll_user as module
from lunch_buddies.types import UsersToPollMessage
from lunch_buddies.lib.service_context import service_context
from tests.fixtures import team


def test_poll_user(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_polls: MockerFixture,
    mocked_slack: MockerFixture,
) -> None:
    module.poll_user(
        UsersToPollMessage(
            team_id="123",
            user_id="test_user_id",
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
    )

    service_context.clients.slack.post_message.assert_called_with(  # type: ignore
        bot_access_token=team.bot_access_token,
        attachments=[
            {
                "fallback": "Something has gone wrong.",
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [
                    {
                        "name": "answer",
                        "text": "Yes (11:30)",
                        "type": "button",
                        "value": "yes_1130",
                    },
                    {
                        "name": "answer",
                        "text": "Yes (12:30)",
                        "type": "button",
                        "value": "yes_1230",
                    },
                    {"name": "answer", "text": "No", "type": "button", "value": "no"},
                ],
            }
        ],
        channel="test_user_id",
        as_user=True,
        text="Are you able to participate in Lunch Buddies today?",
    )
