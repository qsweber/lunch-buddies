import random
from uuid import UUID

from pytest_mock import MockerFixture

from lunch_buddies.models.groups import Group
from lunch_buddies.clients.slack import PostMessageResponse, OpenConversationResponse
from lunch_buddies.lib.service_context import service_context
import lunch_buddies.actions.notify_group as module
from lunch_buddies.types import GroupsToNotifyMessage
from tests.fixtures import team


def test_notify_group(
    mocker: MockerFixture, mocked_polls: MockerFixture, mocked_slack: MockerFixture
) -> None:
    mocker.patch.object(
        service_context.daos.teams,
        "read",
        auto_spec=True,
        return_value=[team._replace(feature_notify_in_channel=False)],
    )

    mocker.patch.object(
        service_context.daos.groups,
        "create",
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        service_context.clients.slack,
        "open_conversation",
        auto_spec=True,
        return_value=OpenConversationResponse(channel_id="new_group_message_channel"),
    )
    random.seed(0)

    module.notify_group(
        GroupsToNotifyMessage(
            team_id="123",
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            response="yes_1130",
            user_ids=["user_id_one", "user_id_two"],
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
        service_context.daos.groups,
    )

    service_context.daos.groups.create.assert_called_with(  # type: ignore
        Group(
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            user_ids=["user_id_one", "user_id_two"],
            response_key="yes_1130",
        ),
    )

    assert service_context.clients.slack.post_message.call_count == 1  # type: ignore

    service_context.clients.slack.post_message.assert_called_with(  # type: ignore
        bot_access_token=team.bot_access_token,
        channel="new_group_message_channel",
        as_user=True,
        text="Hello! This is your group for today. You all should meet somewhere at `11:30`. I am selecting <@user_id_two> to be in charge of picking the location.",
    )


def test_notify_group_feature_notify_in_channel(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_polls: MockerFixture,
    mocked_slack: MockerFixture,
) -> None:
    mocker.patch.object(
        service_context.daos.groups,
        "create",
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        service_context.clients.slack,
        "post_message",
        auto_spec=True,
        return_value=PostMessageResponse(ts="fake_thread_ts"),
    )
    random.seed(0)

    module.notify_group(
        GroupsToNotifyMessage(
            team_id="123",
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            response="yes_1130",
            user_ids=["user_id_one", "user_id_two"],
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
        service_context.daos.groups,
    )

    service_context.daos.groups.create.assert_called_with(  # type: ignore
        Group(
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            user_ids=["user_id_one", "user_id_two"],
            response_key="yes_1130",
        ),
    )

    assert service_context.clients.slack.post_message.call_count == 2  # type: ignore

    service_context.clients.slack.post_message.assert_has_calls(  # type: ignore
        [
            mocker.call(
                bot_access_token=team.bot_access_token,
                channel="test_channel_id",
                as_user=True,
                text="Hey <@user_id_one>, <@user_id_two>! This is your group for today. You all should meet somewhere at `11:30`.",
            ),
            mocker.call(
                bot_access_token=team.bot_access_token,
                channel="test_channel_id",
                as_user=True,
                thread_ts="fake_thread_ts",
                text="<@user_id_two> should pick the location.",
            ),
        ]
    )


def test_notify_group_feature_notify_in_channel_removes_users_that_left(
    mocker: MockerFixture,
    mocked_team: MockerFixture,
    mocked_polls: MockerFixture,
    mocked_slack: MockerFixture,
) -> None:
    mocker.patch.object(
        service_context.daos.groups,
        "create",
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        service_context.clients.slack,
        "post_message",
        auto_spec=True,
        return_value=PostMessageResponse(ts="fake_thread_ts"),
    )
    random.seed(0)

    module.notify_group(
        GroupsToNotifyMessage(
            team_id="123",
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            response="yes_1130",
            user_ids=["user_id_one", "user_id_two", "user_id_three_that_left"],
        ),
        service_context.clients.slack,
        service_context.daos.polls,
        service_context.daos.teams,
        service_context.daos.groups,
    )

    service_context.daos.groups.create.assert_called_with(  # type: ignore
        Group(
            callback_id=UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
            user_ids=["user_id_one", "user_id_two", "user_id_three_that_left"],
            response_key="yes_1130",
        ),
    )

    assert service_context.clients.slack.post_message.call_count == 2  # type: ignore

    service_context.clients.slack.post_message.assert_has_calls(  # type: ignore
        [
            mocker.call(
                bot_access_token=team.bot_access_token,
                channel="test_channel_id",
                as_user=True,
                text="Hey <@user_id_one>, <@user_id_two>! This is your group for today. You all should meet somewhere at `11:30`.",
            ),
            mocker.call(
                bot_access_token=team.bot_access_token,
                channel="test_channel_id",
                as_user=True,
                thread_ts="fake_thread_ts",
                text="<@user_id_two> should pick the location.",
            ),
        ]
    )
