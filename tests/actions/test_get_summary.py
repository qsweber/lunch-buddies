from datetime import datetime
import uuid

import pytest

from lunch_buddies.constants.polls import CHOICES, CLOSED
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.models.polls import Poll
import lunch_buddies.actions.get_summary as module


def test_get_summary_for_poll(mocker):
    mocker.patch.object(
        service_context.daos.groups,
        "_read_internal",
        auto_spec=True,
        return_value=[
            {
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "user_ids": '["abc", "def"]',
                "response_key": "yes_1200",
            },
        ],
    )

    actual = module._get_summary_for_poll(
        Poll(
            team_id="123",
            created_at=datetime.fromtimestamp(float("1549513085.234873")),
            channel_id="test_channel_id",
            created_by_user_id="456",
            callback_id=uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            state=CLOSED,
            choices=CHOICES,
            group_size=5,
            stripe_invoice_id=None,
        ),
        service_context.daos.groups,
        "America/New_York",
    )

    assert (
        actual
        == """*February 06, 2019: started by* <@456>\nYes (12:00): <@abc> <@def>"""
    )


@pytest.mark.parametrize(
    "rest_of_command, expected", [(" 4 ", 4), (" asdf ", 7), ("asdf 5", 5)]  # default
)
def test_get_lookback_days(rest_of_command, expected):
    actual = module._get_lookback_days(rest_of_command)

    assert actual == expected