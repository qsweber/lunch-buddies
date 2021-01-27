import os

import pytest

from lunch_buddies.clients.slack import SlackClient


def test_post_message() -> None:
    client = SlackClient()
    general_channel = client.get_channel(
        os.environ.get("TEST_SLACK_TOKEN") or "", "general"
    )
    response = client.post_message(
        os.environ.get("TEST_SLACK_TOKEN") or "",
        general_channel.channel_id,
        True,
        "hi from tests",
    )
    assert response.ts is not None


def test_post_message_fake_channel() -> None:
    client = SlackClient()
    with pytest.raises(Exception) as excinfo:
        client.post_message(os.environ.get("TEST_SLACK_TOKEN") or "", "foo", True, "hi")

    assert "foo does not exist" == str(excinfo.value)


def test_post_message_if_channel_exists() -> None:
    client = SlackClient()
    general_channel = client.get_channel(
        os.environ.get("TEST_SLACK_TOKEN") or "", "general"
    )
    response = client.post_message_if_channel_exists(
        os.environ.get("TEST_SLACK_TOKEN") or "",
        general_channel.channel_id,
        True,
        "hi from tests",
    )
    assert response and response.ts is not None


def test_post_message_if_channel_exists_fake_channel() -> None:
    client = SlackClient()
    response = client.post_message_if_channel_exists(
        os.environ.get("TEST_SLACK_TOKEN") or "", "foo", True, "hi"
    )
    assert response is None
