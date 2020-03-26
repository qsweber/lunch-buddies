import pytest

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
