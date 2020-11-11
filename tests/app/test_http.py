import os

import pytest

import lunch_buddies.app.http as module
from lunch_buddies.types import CreatePoll
from lunch_buddies.lib.service_context import service_context


def test_validate_request_token():
    os.environ["VERIFICATION_TOKEN"] = "fake_verification_token"

    result = module._validate_request_token("fake_verification_token")

    assert result is True


def test_validate_request_token_finds_dev_token():
    os.environ["VERIFICATION_TOKEN"] = "fake_verification_token"
    os.environ["VERIFICATION_TOKEN_DEV"] = "fake_dev_verification_token"

    result = module._validate_request_token("fake_dev_verification_token")

    assert result is True


def test_validate_request_token_errors_if_does_not_match_either():
    os.environ["VERIFICATION_TOKEN"] = "fake_verification_token"
    os.environ["VERIFICATION_TOKEN_DEV"] = "fake_dev_verification_token"

    with pytest.raises(Exception) as excinfo:
        module._validate_request_token("foo")

    assert "you are not authorized to call this URL" == str(excinfo.value)


def test_validate_team(mocker, mocked_team):
    result = module._validate_team("123", service_context.daos.teams)

    assert result is True


def test_validate_team_fails_if_invalid_team(mocker):
    mocker.patch.object(
        service_context.daos.teams, "_read_internal", auto_spec=True, return_value=[]
    )

    with pytest.raises(Exception) as excinfo:
        module._validate_team("foo", service_context.daos.teams)

    assert "your team is not authorized for this app" == str(excinfo.value)


@pytest.fixture
def client():
    client = module.app.test_client()

    yield client


def test_create_poll_http(mocker, client):
    os.environ["VERIFICATION_TOKEN"] = "test_token"

    mocked_queue_create_poll = mocker.patch.object(
        module,
        "queue_create_poll",
        return_value=None,
        auto_spec=True,
    )

    mocker.patch.object(
        module,
        "_validate_team",
        return_value=None,
        auto_spec=True,
    )

    client.post(
        "/api/v0/poll/create",
        data={
            "token": "test_token",
            "team_id": "T0001",
            "team_domain": "example",
            "channel_id": "C2147483705",
            "channel_name": "test",
            "user_id": "U2147483697",
            "user_name": "Steve",
            "command": "/weather",
            "text": "94070",
            "response_url": "https://hooks.slack.com/commands/1234/5678",
            "trigger_id": "13345224609.738474920.8088930838d88f008e0",
        },
    )

    mocked_queue_create_poll.assert_called_with(
        CreatePoll(
            text="94070", team_id="T0001", channel_id=None, user_id="U2147483697"
        ),
        service_context,
    )
