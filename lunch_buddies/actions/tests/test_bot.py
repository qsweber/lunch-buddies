import pytest

from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants.help import APP_EXPLANATION
from lunch_buddies.types import BotMention, CreatePoll, ClosePoll
import lunch_buddies.actions.bot as module


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


def test_bot_help(mocker):
    result = module.bot(
        BotMention(
            team_id='test_team_id',
            channel_id='foo',
            user_id='foo',
            text='<@BOT> help',
        ),
        None,
    )

    assert result == APP_EXPLANATION


def test_bot_create(mocker):
    sqs_client = SqsClient()

    mocked = mocker.patch.object(
        module,
        'queue_create_poll',
        return_value='ok',
        auto_spec=True,
    )

    module.bot(
        BotMention(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='<@BOT> create 1130',
        ),
        sqs_client,
    )

    mocked.assert_called_with(
        CreatePoll(
            text='1130',
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
        ),
        sqs_client,
    )


def test_bot_close(mocker):
    sqs_client = SqsClient()

    mocked = mocker.patch.object(
        module,
        'queue_close_poll',
        return_value='ok',
        auto_spec=True,
    )

    module.bot(
        BotMention(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='<@BOT> close',
        ),
        sqs_client,
    )

    mocked.assert_called_with(
        ClosePoll(
            text='',
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
        ),
        sqs_client,
    )
