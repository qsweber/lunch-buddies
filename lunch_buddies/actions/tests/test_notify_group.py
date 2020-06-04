import random
from uuid import UUID

from lunch_buddies.lib.service_context import service_context
import lunch_buddies.actions.notify_group as module
from lunch_buddies.types import GroupsToNotifyMessage
from lunch_buddies.actions.tests.fixtures import team, dynamo_team


def test_notify_group(mocker, mocked_polls, mocked_slack):
    mocker.patch.object(
        service_context.daos.teams,
        "_read_internal",
        auto_spec=True,
        return_value=[{**dynamo_team, "feature_notify_in_channel": 0}],
    )

    mocked_groups_dao_create_internal = mocker.patch.object(
        service_context.daos.groups,
        "_create_internal",
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        service_context.clients.slack,
        "open_conversation",
        auto_spec=True,
        return_value={"channel": {"id": "new_group_message_channel"}},
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

    expected_group = {
        "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
        "user_ids": '["user_id_one", "user_id_two"]',
        "response_key": "yes_1130",
    }

    mocked_groups_dao_create_internal.assert_called_with(expected_group,)

    assert service_context.clients.slack.post_message.call_count == 1

    service_context.clients.slack.post_message.assert_called_with(
        bot_access_token=team.bot_access_token,
        channel="new_group_message_channel",
        as_user=True,
        text="Hello! This is your group for today. You all should meet somewhere at `11:30`. I am selecting <@user_id_two> to be in charge of picking the location.",
    )


def test_notify_group_feature_notify_in_channel(
    mocker, mocked_team, mocked_polls, mocked_slack
):
    mocked_groups_dao_create_internal = mocker.patch.object(
        service_context.daos.groups,
        "_create_internal",
        auto_spec=True,
        return_value=True,
    )

    mocker.patch.object(
        service_context.clients.slack,
        "post_message",
        auto_spec=True,
        return_value={"ts": "fake_thread_ts"},
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

    mocked_groups_dao_create_internal.assert_called_with(
        {
            "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
            "user_ids": '["user_id_one", "user_id_two"]',
            "response_key": "yes_1130",
        }
    )

    assert service_context.clients.slack.post_message.call_count == 2

    service_context.clients.slack.post_message.assert_has_calls(
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
