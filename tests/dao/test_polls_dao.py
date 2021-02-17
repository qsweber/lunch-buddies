from datetime import datetime
import uuid

import pytest
from pytest_mock import MockerFixture
from dynamo_dao import DynamoObject

from lunch_buddies.lib.service_context import service_context
from lunch_buddies.models.polls import Poll, Choice
from tests.fixtures import poll


@pytest.mark.parametrize(
    "model, dynamo",
    [
        (
            poll,
            {
                "team_id": "123",
                "created_at": 1522117983.551714,
                "channel_id": "test_channel_id",
                "created_by_user_id": "456",
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "state": "CREATED",
                "choices": '[{"key": "yes_1130", "is_yes": true, "time": "11:30", "display_text": "Yes (11:30)"}, {"key": "yes_1230", "is_yes": true, "time": "12:30", "display_text": "Yes (12:30)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                "group_size": 6,
                "stripe_invoice_id": None,
            },
        ),
        (
            Poll(
                team_id="123",
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id="test_channel_id",
                created_by_user_id="456",
                callback_id=uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
                state="CREATED",
                choices=[
                    Choice(
                        key="yes_1200",
                        is_yes=True,
                        time="12:00",
                        display_text="Yes (12:00)",
                    ),
                    Choice(
                        key="no",
                        is_yes=False,
                        time="",
                        display_text="No",
                    ),
                ],
                group_size=6,
                stripe_invoice_id="fake-stripe-invoice-id",
            ),
            {
                "team_id": "123",
                "created_at": 1522117983.551714,
                "channel_id": "test_channel_id",
                "created_by_user_id": "456",
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "state": "CREATED",
                "choices": '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                "group_size": 6,
                "stripe_invoice_id": "fake-stripe-invoice-id",
            },
        ),
        (
            Poll(
                team_id="123",
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id="OLD_POLL",
                created_by_user_id="456",
                callback_id=uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
                state="CREATED",
                choices=[
                    Choice(
                        key="yes_1200",
                        is_yes=True,
                        time="12:00",
                        display_text="Yes (12:00)",
                    ),
                    Choice(
                        key="no",
                        is_yes=False,
                        time="",
                        display_text="No",
                    ),
                ],
                group_size=6,
                stripe_invoice_id="fake-stripe-invoice-id",
            ),
            {
                "team_id": "123",
                "created_at": 1522117983.551714,
                "channel_id": None,
                "created_by_user_id": "456",
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "state": "CREATED",
                "choices": '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                "group_size": 6,
                "stripe_invoice_id": "fake-stripe-invoice-id",
            },
        ),
    ],
)
def test_roundtrip_convert(model: Poll, dynamo: DynamoObject) -> None:
    to_dynamo = service_context.daos.polls.convert_to_dynamo(model)

    assert to_dynamo == dynamo

    from_dynamo = service_context.daos.polls.convert_from_dynamo(to_dynamo)

    assert from_dynamo == model


@pytest.mark.parametrize(
    "dynamo, expected",
    [
        (
            {
                "team_id": "123",
                "created_at": 1522117983.551714,
                "channel_id": "test_channel_id",
                "created_by_user_id": "456",
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "state": "CREATED",
                "choices": '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                "group_size": 6,
            },
            Poll(
                team_id="123",
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id="test_channel_id",
                created_by_user_id="456",
                callback_id=uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
                state="CREATED",
                choices=[
                    Choice(
                        key="yes_1200",
                        is_yes=True,
                        time="12:00",
                        display_text="Yes (12:00)",
                    ),
                    Choice(
                        key="no",
                        is_yes=False,
                        time="",
                        display_text="No",
                    ),
                ],
                group_size=6,
                stripe_invoice_id=None,
            ),
        ),
        (
            {
                "team_id": "123",
                "created_at": 1522117983.551714,
                "created_by_user_id": "456",
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "state": "CREATED",
                "choices": '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                "group_size": 6,
                "stripe_invoice_id": "fake-stripe-invoice-id",
            },
            Poll(
                team_id="123",
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id="OLD_POLL",
                created_by_user_id="456",
                callback_id=uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
                state="CREATED",
                choices=[
                    Choice(
                        key="yes_1200",
                        is_yes=True,
                        time="12:00",
                        display_text="Yes (12:00)",
                    ),
                    Choice(
                        key="no",
                        is_yes=False,
                        time="",
                        display_text="No",
                    ),
                ],
                group_size=6,
                stripe_invoice_id="fake-stripe-invoice-id",
            ),
        ),
        (
            {
                "team_id": "123",
                "created_at": 1522117983.551714,
                "created_by_user_id": "456",
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "state": "CREATED",
                "choices": '{"yes_1145": "Yes (11:45)", "yes_1230": "Yes (12:30)", "no": "No"}',
                "group_size": 6,
                "stripe_invoice_id": "fake-stripe-invoice-id",
            },
            Poll(
                team_id="123",
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id="OLD_POLL",
                created_by_user_id="456",
                callback_id=uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
                state="CREATED",
                choices=[
                    Choice(
                        key="yes_1145",
                        is_yes=True,
                        time="11:45",
                        display_text="Yes (11:45)",
                    ),
                    Choice(
                        key="yes_1230",
                        is_yes=True,
                        time="12:30",
                        display_text="Yes (12:30)",
                    ),
                    Choice(
                        key="no",
                        is_yes=False,
                        time="",
                        display_text="No",
                    ),
                ],
                group_size=6,
                stripe_invoice_id="fake-stripe-invoice-id",
            ),
        ),
        (
            {
                "team_id": "123",
                "created_at": 1522117983.551714,
                "created_by_user_id": "456",
                "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
                "state": "CREATED",
                "choices": '[["yes_1130", "Yes (11:30)"], ["yes_1230", "Yes (12:30)"], ["no", "No"]]',
                "group_size": 6,
                "stripe_invoice_id": "fake-stripe-invoice-id",
            },
            Poll(
                team_id="123",
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id="OLD_POLL",
                created_by_user_id="456",
                callback_id=uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
                state="CREATED",
                choices=[
                    Choice(
                        key="yes_1130",
                        is_yes=True,
                        time="11:30",
                        display_text="Yes (11:30)",
                    ),
                    Choice(
                        key="yes_1230",
                        is_yes=True,
                        time="12:30",
                        display_text="Yes (12:30)",
                    ),
                    Choice(
                        key="no",
                        is_yes=False,
                        time="",
                        display_text="No",
                    ),
                ],
                group_size=6,
                stripe_invoice_id="fake-stripe-invoice-id",
            ),
        ),
    ],
)
def test_convert_from_dynamo(dynamo: DynamoObject, expected: Poll) -> None:
    poll = service_context.daos.polls.convert_from_dynamo(dynamo)

    assert poll == expected


def test_find_by_callback_id_or_die_no_polls(mocker: MockerFixture) -> None:
    mocker.patch.object(
        service_context.daos.polls, "read", auto_spec=True, return_value=[]
    )

    with pytest.raises(Exception) as excinfo:
        service_context.daos.polls.find_by_callback_id_or_die(
            "123", uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa")
        )

    assert "no polls found for team 123" == str(excinfo.value)


def test_find_by_callback_id_or_die_no_matching_poll(mocker: MockerFixture) -> None:
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[poll],
    )

    with pytest.raises(Exception) as excinfo:
        service_context.daos.polls.find_by_callback_id_or_die(
            "123", uuid.UUID("aaa101f9-9aaa-4899-85c8-aa0a2dbb0aaa")
        )

    assert (
        "poll not found with callback_id aaa101f9-9aaa-4899-85c8-aa0a2dbb0aaa"
        == str(excinfo.value)
    )


def test_find_by_callback_id_or_die_multiple_matching(mocker: MockerFixture) -> None:
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[
            poll,
            poll,
        ],
    )

    with pytest.raises(Exception) as excinfo:
        service_context.daos.polls.find_by_callback_id_or_die("123", poll.callback_id)

    assert (
        "more than one poll found with callback_id f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"
        == str(excinfo.value)
    )


def test_mark_poll_closed(mocker: MockerFixture) -> None:
    mocker.patch.object(
        service_context.daos.polls,
        "update",
        auto_spec=True,
        return_value=None,
    )

    service_context.daos.polls.mark_poll_closed(poll)

    service_context.daos.polls.update.assert_called_with(  # type: ignore
        poll, poll._replace(state="CLOSED")
    )
