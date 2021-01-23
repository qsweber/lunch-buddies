from datetime import datetime, timedelta
from uuid import UUID
import typing

import pytest
from pytest_mock import MockerFixture

import lunch_buddies.actions.invoice as module
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.clients.stripe import Invoice, Customer, LineItem
from tests.fixtures import (
    team,
    poll,
    poll_response,
)


@pytest.fixture
def mocked_data(mocker: MockerFixture) -> None:
    mocker.patch.object(
        module, "_get_now", auto_spec=True, return_value=datetime(2020, 3, 16, 3, 3, 3)
    )
    mocker.patch.object(
        service_context.daos.teams,
        "read",
        auto_spec=True,
        return_value=[
            team._replace(created_at=datetime(2020, 1, 31)),
        ],
    )
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[
            poll._replace(
                state="CLOSED",
                created_at=datetime(2020, 3, 15),
            ),
        ],
    )
    mocker.patch.object(
        service_context.daos.poll_responses,
        "read",
        auto_spec=True,
        return_value=[poll_response._replace(user_id=str(i)) for i in range(11)],
    )
    mocker.patch.object(
        service_context.clients.stripe,
        "latest_invoice_for_customer",
        auto_spec=True,
        return_value=None,
    )
    mocker.patch.object(
        service_context.clients.stripe,
        "create_invoice",
        auto_spec=True,
        return_value=Invoice(id="new-stripe-invoice-id", created_at=datetime.now()),
    )
    mocker.patch.object(
        service_context.daos.polls,
        "mark_poll_invoiced",
        auto_spec=True,
        return_value=None,
    )


def test_invoice(mocker: MockerFixture, mocked_data: MockerFixture) -> None:
    module.invoice(service_context, False)

    service_context.clients.stripe.create_invoice.assert_called_with(  # type: ignore
        Customer(
            id=team.stripe_customer_id,  # type: ignore
        ),
        [
            LineItem(
                amount=11.0,
                description="11 people responded Yes to a Lunch Buddies poll since 2020-03-01",
            ),
        ],
    )

    service_context.daos.polls.mark_poll_invoiced.assert_called_with(  # type: ignore
        poll._replace(state="CLOSED", created_at=datetime(2020, 3, 15)),
        "new-stripe-invoice-id",
    )


def test_invoice_dry_run(mocker: MockerFixture, mocked_data: MockerFixture) -> None:
    module.invoice(service_context, True)

    service_context.clients.stripe.create_invoice.assert_not_called()  # type: ignore

    service_context.daos.polls.mark_poll_invoiced.assert_not_called()  # type: ignore


def test_invoice_line_item_zero(
    mocker: MockerFixture, mocked_data: MockerFixture
) -> None:
    mocker.patch.object(
        service_context.daos.poll_responses,
        "read",
        auto_spec=True,
        return_value=[
            poll_response._replace(user_id=str(i), response="no") for i in range(11)
        ],
    )
    module.invoice(service_context, True)

    service_context.clients.stripe.create_invoice.assert_not_called()  # type: ignore

    service_context.daos.polls.mark_poll_invoiced.assert_not_called()  # type: ignore


def test_invoice_when_not_first_invoice(
    mocker: MockerFixture, mocked_data: MockerFixture
) -> None:
    mocker.patch.object(
        service_context.clients.stripe,
        "latest_invoice_for_customer",
        auto_spec=True,
        return_value=Invoice(
            id="previous",
            created_at=datetime(2020, 2, 14),
        ),
    )

    module.invoice(service_context, False)

    service_context.clients.stripe.create_invoice.assert_called_with(  # type: ignore
        Customer(
            id=team.stripe_customer_id,  # type: ignore
        ),
        [
            LineItem(
                amount=11.0,
                description="11 people responded Yes to a Lunch Buddies poll since 2020-02-14",
            ),
        ],
    )


def test_find_teams_eligible_for_invoicing(mocker: MockerFixture) -> None:
    base_team = team._replace(created_at=datetime(2020, 1, 31))
    mocker.patch.object(
        module, "_get_now", auto_spec=True, return_value=datetime(2020, 3, 16, 3, 3, 3)
    )

    mocker.patch.object(
        service_context.daos.teams,
        "read",
        auto_spec=True,
        return_value=[
            base_team._replace(team_id="1"),
            base_team._replace(
                team_id="2",
                stripe_customer_id=None,
                invoicing_enabled=True,
            ),
            base_team._replace(
                team_id="3",
                stripe_customer_id="fake-customer-id",
                invoicing_enabled=False,
            ),
            base_team._replace(
                team_id="4",
                created_at=datetime(2020, 2, 1),
            ),
        ],
    )
    result = module._find_teams_eligible_for_invoicing(service_context)

    assert [t.team_id for t in result] == ["1"]


@pytest.mark.parametrize(
    "now, created_ats, expected",
    [
        (datetime(2020, 3, 16), [datetime(2020, 2, 15), datetime(2020, 1, 31)], [1]),
        (datetime(2020, 3, 2), [datetime(2020, 2, 15), datetime(2020, 1, 31)], [1]),
        (datetime(2020, 4, 2), [datetime(2020, 2, 15), datetime(2020, 1, 31)], [0, 1]),
    ],
)
def test_find_teams_eligible_for_invoicing_created_at(
    mocker: MockerFixture,
    now: datetime,
    created_ats: typing.List[datetime],
    expected: typing.List[int],
) -> None:
    mocker.patch.object(module, "_get_now", auto_spec=True, return_value=now)

    mocker.patch.object(
        service_context.daos.teams,
        "read",
        auto_spec=True,
        return_value=[
            team._replace(team_id=str(index), created_at=created_at)
            for index, created_at in enumerate(created_ats)
        ],
    )

    result = module._find_teams_eligible_for_invoicing(service_context)

    assert [int(t.team_id) for t in result] == expected


def test_get_polls_needing_invoice(mocker: MockerFixture) -> None:
    mocker.patch.object(
        service_context.daos.polls,
        "read",
        auto_spec=True,
        return_value=[
            poll._replace(
                callback_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"),
                stripe_invoice_id=None,
                state="CLOSED",
                created_at=(team.created_at + timedelta(days=29)),
            ),
            poll._replace(
                callback_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"),
                stripe_invoice_id=None,
                state="CLOSED",
                created_at=(team.created_at + timedelta(days=30)),
            ),
            poll._replace(
                callback_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"),
                stripe_invoice_id=None,
                state="CLOSED",
                created_at=(team.created_at + timedelta(days=31)),
            ),
            poll._replace(
                callback_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4"),
                stripe_invoice_id=None,
                state="CREATED",
                created_at=(team.created_at + timedelta(days=31)),
            ),
            poll._replace(
                callback_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5"),
                stripe_invoice_id="fake",
                state="CLOSED",
                created_at=(team.created_at + timedelta(days=31)),
            ),
        ],
    )

    result = module._get_polls_needing_invoice(service_context, team)

    assert [p.callback_id for p in result] == [
        UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3")
    ]


def test_get_unique_yes_users_from_polls(mocker: MockerFixture) -> None:
    mocker.patch.object(
        service_context.daos.poll_responses,
        "read",
        auto_spec=True,
        return_value=[
            poll_response._replace(user_id="1", response="yes_1145"),
            poll_response._replace(user_id="2", response="no"),
            poll_response._replace(user_id="3", response="yes_1145"),
            poll_response._replace(user_id="1", response="yes_1145"),
        ],
    )

    result = module._get_unique_yes_users_from_polls(service_context, [poll])

    assert sorted(result) == ["1", "3"]
