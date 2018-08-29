import pytest

import lunch_buddies.actions.bot as module
from lunch_buddies.types import BotMention


@pytest.mark.parametrize(
    'text, expected',
    [
        ('<@123> hello there', ('hello', 'there')),
        ('<@123> hello there today', ('hello', 'there today')),
        ('<@123> create 1130, 1230', ('create', '1130, 1230')),
    ]
)
def test_parse_text(text, expected):
    actual = module._parse_text(text)

    assert actual == expected


@pytest.mark.parametrize(
    'text, expected',
    [
        ('hello there', ('hello', 'there')),
        (' hello there today  ', ('hello', 'there today')),
    ]
)
def test_split_text(text, expected):
    actual = module._split_text(text)

    assert actual == expected


def test_bot_create(mocker):

    module.bot(
        message=BotMention(
            team_id='str',
            channel_id='str',
            user_id='str',
            text='str',
        ),
        sqs_client: SqsClient,
        teams_dao: TeamsDao,
    )