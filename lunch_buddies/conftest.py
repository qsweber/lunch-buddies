import pytest

from lunch_buddies.actions.tests.fixtures import dynamo_team, stripe_customer
from lunch_buddies.lib.service_context import service_context


@pytest.fixture
def mocked_sqs_v2(mocker):
    mocker.patch.object(
        service_context.clients.sqs_v2,
        'send_messages',
        auto_spec=True,
        return_value=True,
    )


@pytest.fixture
def mocked_slack(mocker):
    mocker.patch.object(
        service_context.clients.slack,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        service_context.clients.slack,
        '_channels_list_internal',
        auto_spec=True,
        return_value=[
            {'name': 'lunch_buddies', 'id': 'slack_channel_id'},
            {'name': 'foo', 'id': 'foo'},
        ]
    )

    mocker.patch.object(
        service_context.clients.slack,
        '_channel_members',
        auto_spec=True,
        return_value=['user_id_one', 'user_id_two']
    )


@pytest.fixture
def mocked_team(mocker):
    mocker.patch.object(
        service_context.daos.teams,
        '_read_internal',
        auto_spec=True,
        return_value=[dynamo_team]
    )


@pytest.fixture
def mocked_stripe(mocker):
    mocker.patch.object(
        service_context.clients.stripe,
        'create_customer',
        auto_spec=True,
        return_value=stripe_customer,
    )


@pytest.fixture
def mocked_polls(mocker):
    mocker.patch.object(
        service_context.daos.polls,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'team_id': '123',
                'created_at': float(1586645982.850783),
                'channel_id': 'test_channel_id',
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': 'CREATED',
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': 6,
            },
            {
                'team_id': '123',
                'created_at': float(1586645992.227006),
                'channel_id': 'test_channel_id',
                'created_by_user_id': 'foo',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
                'state': 'CREATED',
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': 6,
            },
        ]
    )
    mocker.patch.object(
        service_context.daos.polls,
        'mark_poll_closed',
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        service_context.daos.polls,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
