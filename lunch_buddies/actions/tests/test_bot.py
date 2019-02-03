from datetime import datetime

import pytest

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants.help import APP_EXPLANATION
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
from lunch_buddies.types import BotMention, CreatePoll, ClosePoll
import lunch_buddies.actions.bot as module


@pytest.mark.parametrize(
    'text, expected',
    [
        ('<@123> hello there', ('hello', 'there')),
        ('<@123> hello there today', ('hello', 'there today')),
        ('<@123> create 1130, 1230', ('create', '1130, 1230')),
        ('Reminder: <@U8PRM6XHN|lunch_buddies> create 1123.', ('create', '1123')),
        ('Reminder: create 1123.', None),
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
    teams_dao = TeamsDao()
    created_at = datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'name': 'fake-team-name',
            'bot_access_token': 'fake-bot-token',
            'created_at': created_at.timestamp(),
        }]
    )
    slack_client = SlackClient()
    mocked_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

    module.bot(
        BotMention(
            team_id='test_team_id',
            channel_id='foo',
            user_id='foo',
            text='<@BOT> help',
        ),
        None,
        slack_client,
        teams_dao,
        None,
        None,
    )

    mocked_post_message.assert_called_with(
        team=Team(
            team_id='123',
            access_token='fake-token',
            name='fake-team-name',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel='foo',
        as_user=True,
        text=APP_EXPLANATION,
    )


def test_bot_create(mocker):
    teams_dao = TeamsDao()
    created_at = datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'name': 'fake-team-name',
            'bot_access_token': 'fake-bot-token',
            'created_at': created_at.timestamp(),
        }]
    )

    slack_client = SlackClient()
    mocked_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

    sqs_client = SqsClient()
    mocked_queue_create_poll = mocker.patch.object(
        module,
        'queue_create_poll',
        return_value='mocked_return_value',
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
        slack_client,
        teams_dao,
        None,
        None,
    )

    mocked_queue_create_poll.assert_called_with(
        CreatePoll(
            text='1130',
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
        ),
        sqs_client,
    )

    mocked_post_message.assert_called_with(
        team=Team(
            team_id='123',
            access_token='fake-token',
            name='fake-team-name',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel='test_channel_id',
        as_user=True,
        text='mocked_return_value',
    )


def test_bot_close(mocker):
    teams_dao = TeamsDao()
    created_at = datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'name': 'fake-team-name',
            'bot_access_token': 'fake-bot-token',
            'created_at': created_at.timestamp(),
        }]
    )

    slack_client = SlackClient()
    mocked_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

    sqs_client = SqsClient()

    mocked = mocker.patch.object(
        module,
        'queue_close_poll',
        return_value='mocked_return_value',
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
        slack_client,
        teams_dao,
        None,
        None,
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

    mocked_post_message.assert_called_with(
        team=Team(
            team_id='123',
            access_token='fake-token',
            name='fake-team-name',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel='test_channel_id',
        as_user=True,
        text='mocked_return_value',
    )
