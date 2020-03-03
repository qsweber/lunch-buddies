from datetime import datetime

import pytest

from lunch_buddies.constants.help import APP_EXPLANATION
from lunch_buddies.models.teams import Team
from lunch_buddies.types import BotMention, CreatePoll, ClosePoll
import lunch_buddies.actions.bot as module
from lunch_buddies.lib.service_context import service_context


@pytest.mark.parametrize(
    'text, message_type, expected',
    [
        # message_type=app_mention
        ('<@123> hello there', 'app_mention', ('hello', 'there')),
        ('<@123> hello there today', 'app_mention', ('hello', 'there today')),
        ('<@123> create 1130, 1230', 'app_mention', ('create', '1130, 1230')),
        ('Reminder: <@U8PRM6XHN|lunch_buddies> create 1123.', 'app_mention', ('create', '1123')),
        ('Reminder: create 1123.', 'app_mention', None),
        # message_type=message
        ('<@123> hello there', 'message', ('hello', 'there')),
        ('<@123> hello there today', 'message', ('hello', 'there today')),
        ('<@123> create 1130, 1230', 'message', ('create', '1130, 1230')),
        ('Reminder: <@U8PRM6XHN|lunch_buddies> create 1123.', 'message', ('create', '1123')),
        ('Reminder: create 1123.', 'message', ('reminder:', 'create 1123')),
        ('create 1123', 'message', ('create', '1123')),
        ('summary', 'message', ('summary', '')),
    ]
)
def test_parse_message(text, message_type, expected):
    message = BotMention(
        team_id='foo',
        channel_id='foo',
        user_id='foo',
        text=text,
        message_type=message_type,
    )
    actual = module._parse_message(message)

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
    created_at = datetime.now()
    mocker.patch.object(
        service_context.daos.teams,
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
    mocked_post_message = mocker.patch.object(
        service_context.clients.slack,
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
            message_type='app_mention',
        ),
        service_context,
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
    created_at = datetime.now()
    mocker.patch.object(
        service_context.daos.teams,
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

    mocked_post_message = mocker.patch.object(
        service_context.clients.slack,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

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
            message_type='app_mention',
        ),
        service_context,
    )

    mocked_queue_create_poll.assert_called_with(
        CreatePoll(
            text='1130',
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
        ),
        service_context.clients.sqs,
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
    created_at = datetime.now()
    mocker.patch.object(
        service_context.daos.teams,
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

    mocked_post_message = mocker.patch.object(
        service_context.clients.slack,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

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
            message_type='app_mention',
        ),
        service_context,
    )

    mocked.assert_called_with(
        ClosePoll(
            text='',
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
        ),
        service_context.clients.sqs,
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
