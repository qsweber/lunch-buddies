from datetime import datetime
import os

import pytest

from lunch_buddies.dao.teams import TeamsDao
import lunch_buddies.app.http as module


def test_validate_request_token():
    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    result = module._validate_request_token('fake_verification_token')

    assert result is True


def test_validate_request_token_finds_dev_token():
    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'
    os.environ['VERIFICATION_TOKEN_DEV'] = 'fake_dev_verification_token'

    result = module._validate_request_token('fake_dev_verification_token')

    assert result is True


def test_validate_request_token_errors_if_does_not_match_either():
    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'
    os.environ['VERIFICATION_TOKEN_DEV'] = 'fake_dev_verification_token'

    with pytest.raises(Exception) as excinfo:
        module._validate_request_token('foo')

    assert 'you are not authorized to call this URL' == str(excinfo.value)


def test_validate_team(mocker):
    teams_dao = TeamsDao()
    created_at = datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': created_at.timestamp(),
        }]
    )

    result = module._validate_team('123', teams_dao)

    assert result is True


def test_validate_team_fails_if_invalid_team(mocker):
    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[]
    )

    with pytest.raises(Exception) as excinfo:
        module._validate_team('foo', teams_dao)

    assert 'your team is not authorized for this app' == str(excinfo.value)


def test_listen_to_poll_http(mocker):
    # request_payload = {
    #     'type': 'interactive_message',
    #     'actions': [{
    #         'name': 'answer',
    #         'type': 'button',
    #         'value': 'yes_1200'
    #     }],
    #     'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
    #     'team': {
    #         'id': 'fake_team_id',
    #     },
    #     'channel': {
    #         'id': 'fake_channel_id',
    #         'name': 'directmessage'
    #     },
    #     'user': {
    #         'id': 'fake_user_id',
    #         'name': 'quinnsweber'
    #     },
    #     'action_ts': '1516117984.234873',
    #     'message_ts': '1516117976.000223',
    #     'attachment_id': '1',
    #     'token': 'fake_verification_token',
    #     'is_app_unfurl': False,
    #     'original_message': {
    #         'text': 'Are you able to participate in Lunch Buddies today?',
    #         'username': 'Lunch Buddies',
    #         'bot_id': 'fake_bot_id',
    #         'attachments': [{
    #             'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb07cb',
    #             'fallback': 'Something has gone wrong.',
    #             'id': 1,
    #             'color': '3AA3E3',
    #             'actions': [{
    #                 'id': '1',
    #                 'name': 'answer',
    #                 'text': 'Yes (12:00)',
    #                 'type': 'button',
    #                 'value': 'yes_1200',
    #                 'style': '',
    #             }, {
    #                 'id': '2',
    #                 'name': 'answer',
    #                 'text': 'No',
    #                 'type': 'button',
    #                 'value': 'no',
    #                 'style': '',
    #             }]
    #         }],
    #         'type': 'message',
    #         'subtype': 'bot_message',
    #         'ts': '1516117976.000223',
    #     },
    #     'response_url': 'fake_response_url',
    #     'trigger_id': 'fake_trigger_id',
    # }

    # TODO: do this

    assert 1 == 1

# OAUTH_RESPONSE = {
#     "access_token": "xoxp-XXXXXXXX-XXXXXXXX-XXXXX",
#     "scope": "incoming-webhook,commands,bot",
#     "team_name": "Team Installing Your Hook",
#     "team_id": "123",
#     "incoming_webhook": {
#         "url": "https://hooks.slack.com/TXXXXX/BXXXXX/XXXXXXXXXX",
#         "channel": "#channel-it-will-post-to",
#         "configuration_url": "https://teamname.slack.com/services/BXXXXX"
#     },
#     "bot": {
#         "bot_user_id": "UTTTTTTTTTTR",
#         "bot_access_token": "xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT"
#     }
# }

# BOT_EVENT = {
#     "token": "prod_verification_token",
#     "team_id": "test_team_id",
#     "api_app_id": "test_api_app_id",
#     "event": {
#         "type": "app_mention",
#         "user": "test_user_id",
#         "text": "<@TESTBOTID> foo",
#         "ts": "1521695530.000170",
#         "channel": "test_channel_id",
#         "event_ts": 1521695530000170
#     },
#     "type": "event_callback",
#     "event_id": "test_event_id",
#     "event_time": 1521695530000170,
#     "authed_users": ["test_authed_user_id"]
# }
