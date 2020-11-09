import uuid
from datetime import datetime

from lunch_buddies.models.polls import Poll, Choice
from lunch_buddies.models.teams import Team
from lunch_buddies.models.groups import Group
from lunch_buddies.models.poll_responses import PollResponse
from lunch_buddies.clients.stripe import Customer


dynamo_team = {
    "team_id": "123",
    "access_token": "DEPRECATED",
    "name": "fake-team-name",
    "bot_access_token": "fake-bot-token",
    "created_at": 1585153363.983078,
    "feature_notify_in_channel": 1,
    "stripe_customer_id": "fake-stripe-customer-id",
    "invoicing_enabled": 1,
}

team = Team(
    team_id="123",
    access_token="DEPRECATED",
    name="fake-team-name",
    bot_access_token="fake-bot-token",
    created_at=datetime.fromtimestamp(1585153363.983078),
    feature_notify_in_channel=True,
    stripe_customer_id="fake-stripe-customer-id",
    invoicing_enabled=True,
)

oath_response = {
    "ok": True,
    "access_token": "fake-token",
    "scope": "identify,bot,commands,channels:write,chat:write:bot",
    "user_id": "fake-user-id",
    "team_name": "fake-team-name",
    "team_id": "123",
    "bot": {"bot_user_id": "U8PRM6XHN", "bot_access_token": "fake-bot-token"},
}

oauth2_response = {
    "ok": True,
    "app_id": "foo",
    "authed_user": {"id": "fake-user-id"},
    "scope": "channels:read,chat:write,commands,groups:read,im:history,im:read,im:write,mpim:history,mpim:read,mpim:write,team:read,users:read,users:read.email,users:write",
    "token_type": "bot",
    "access_token": "fake-bot-token",
    "bot_user_id": "U8PRM6XHN",
    "team": {"id": "123", "name": "fake-team-name"},
    "enterprise": None,
}

stripe_customer = Customer(id="fake-stripe-customer-id")

poll = Poll(
    team_id="123",
    created_at=datetime.fromtimestamp(1522117983.551714),
    channel_id="test_channel_id",
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
    stripe_invoice_id=None,
)

dynamo_poll = {
    "team_id": "123",
    "created_at": 1522117983.551714,
    "channel_id": "test_channel_id",
    "created_by_user_id": "456",
    "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
    "state": "CREATED",
    "choices": '[{"key": "yes_1130", "is_yes": true, "time": "11:30", "display_text": "Yes (11:30)"}, {"key": "yes_1230", "is_yes": true, "time": "12:30", "display_text": "Yes (12:30)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
    "group_size": 6,
    "stripe_invoice_id": None,
}

group = Group(
    callback_id=uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
    user_ids=["abc", "def"],
    response_key="yes_1145",
)

dynamo_group = {
    "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
    "user_ids": '["abc", "def"]',
    "response_key": "yes_1145",
}

poll_response = PollResponse(
    callback_id=uuid.UUID("f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa"),
    user_id="test_user_id",
    created_at=datetime.fromtimestamp(1522117983.551714),
    response="yes_1145",
)

dynamo_poll_response = {
    "callback_id": "f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa",
    "user_id": "test_user_id",
    "created_at": 1522117983.551714,
    "response": "yes_1145",
}
