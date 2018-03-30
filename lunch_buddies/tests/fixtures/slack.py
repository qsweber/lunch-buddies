
OAUTH_RESPONSE = {
    "access_token": "xoxp-XXXXXXXX-XXXXXXXX-XXXXX",
    "scope": "incoming-webhook,commands,bot",
    "team_name": "Team Installing Your Hook",
    "team_id": "123",
    "incoming_webhook": {
        "url": "https://hooks.slack.com/TXXXXX/BXXXXX/XXXXXXXXXX",
        "channel": "#channel-it-will-post-to",
        "configuration_url": "https://teamname.slack.com/services/BXXXXX"
    },
    "bot": {
        "bot_user_id": "UTTTTTTTTTTR",
        "bot_access_token": "xoxb-XXXXXXXXXXXX-TTTTTTTTTTTTTT"
    }
}

BOT_EVENT = {
    "token": "prod_verification_token",
    "team_id": "test_team_id",
    "api_app_id": "test_api_app_id",
    "event": {
        "type": "app_mention",
        "user": "test_user_id",
        "text": "<@TESTBOTID> foo",
        "ts": "1521695530.000170",
        "channel": "test_channel_id",
        "event_ts": 1521695530000170
    },
    "type": "event_callback",
    "event_id": "test_event_id",
    "event_time": 1521695530000170,
    "authed_users": ["test_authed_user_id"]
}
