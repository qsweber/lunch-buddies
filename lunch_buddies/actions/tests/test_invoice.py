from datetime import datetime
from decimal import Decimal

import pytest

import lunch_buddies.actions.invoice as module
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.actions.tests.fixtures import dynamo_team


def test_find_teams_eligible_for_invoicing(mocker):
    now = datetime(2020, 4, 16, 3, 3, 3)
    base_team = {**dynamo_team, 'created_at': Decimal(datetime(2020, 1, 31).timestamp())}
    mocker.patch.object(
        module,
        '_get_now',
        auto_spec=True,
        return_value=now
    )

    mocker.patch.object(
        service_context.daos.teams.dynamo,
        'read',
        auto_spec=True,
        return_value=[
            {
                **base_team,
                'team_id': '1',
            },
            {
                **base_team,
                'team_id': '2',
                'stripe_customer_id': None,
                'invoicing_enabled': 1,
            },
            {
                **base_team,
                'team_id': '3',
                'stripe_customer_id': 'fake-customer-id',
                'invoicing_enabled': 0,
            },
            {
                **base_team,
                'team_id': '4',
                'created_at': Decimal(datetime(2020, 2, 1).timestamp()),
            },
        ]
    )
    result = module._find_teams_eligible_for_invoicing(service_context)

    assert [team.team_id for team in result] == ['1']


@pytest.mark.parametrize(
    'now, created_ats, expected',
    [
        (datetime(2020, 4, 16), [datetime(2020, 2, 15), datetime(2020, 1, 31)], [1]),
        (datetime(2020, 4, 2), [datetime(2020, 2, 15), datetime(2020, 1, 31)], [1]),
    ]
)
def test_find_teams_eligible_for_invoicing_created_at(mocker, now, created_ats, expected):
    mocker.patch.object(
        module,
        '_get_now',
        auto_spec=True,
        return_value=now
    )

    mocker.patch.object(
        service_context.daos.teams.dynamo,
        'read',
        auto_spec=True,
        return_value=[
            {
                **dynamo_team,
                'team_id': str(index),
                'created_at': Decimal(created_at.timestamp()),
            }
            for index, created_at in enumerate(created_ats)
        ]
    )

    result = module._find_teams_eligible_for_invoicing(service_context)

    assert [int(team.team_id) for team in result] == expected


# def test_get_polls_needing_invoice(mocker):
#     mocker.patch.object(
#         service_context.daos.polls.dynamo,
#         'read',
#         auto_spec=True,
#         return_value=[

#         ]
#     )
