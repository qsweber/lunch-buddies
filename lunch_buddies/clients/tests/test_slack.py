from lunch_buddies.lib.service_context import service_context
from lunch_buddies.actions.tests.fixtures import team


users_info = {
    "ok": True,
    "user": {
        "id": "fake-user-id",
        "team_id": "123",
        "name": "foo",
        "deleted": False,
        "color": "9f69e7",
        "real_name": "Real Name",
        "tz": "America/Los_Angeles",
        "tz_label": "Pacific Daylight Time",
        "tz_offset": -25200,
        "profile": {
            "title": "",
            "phone": "",
            "skype": "",
            "real_name": "Real Name",
            "real_name_normalized": "Real Name",
            "display_name": "display_name",
            "display_name_normalized": "display_name",
            "status_text": "",
            "status_emoji": "",
            "status_expiration": 0,
            "avatar_hash": "alajksdf",
            "email": "foo@example.com",
            "first_name": "Real",
            "last_name": "Name",
            "image_24": "url.png",
            "image_32": "url.png",
            "image_48": "url.png",
            "image_72": "url.png",
            "image_192": "url.png",
            "image_512": "url.png",
            "status_text_canonical": "",
            "team": "123",
        },
        "is_admin": True,
        "is_owner": True,
        "is_primary_owner": True,
        "is_restricted": False,
        "is_ultra_restricted": False,
        "is_bot": False,
        "is_app_user": False,
        "updated": 1587338645,
    },
    "headers": {},
}


def test_get_user_name_email(mocker):
    mocker.patch.object(
        service_context.clients.slack,
        "_users_info_internal",
        auto_spec=True,
        return_value=users_info,
    )

    user, email = service_context.clients.slack.get_user_name_email(
        team.bot_access_token, "fake-user-id"
    )

    assert user == "Real Name"
    assert email == "foo@example.com"
