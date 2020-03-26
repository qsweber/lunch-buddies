from lunch_buddies.lib.service_context import service_context
from lunch_buddies.constants.help import CREATE_POLL
from lunch_buddies.constants.queues import PollsToStartMessage
from lunch_buddies.types import CreatePoll
import lunch_buddies.actions.queue_create_poll as module


def test_queue_create_poll(mocked_sqs_v2):
    module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='',
        ),
        service_context,
    )

    service_context.clients.sqs_v2.send_messages.assert_called_with(
        'polls_to_start',
        [PollsToStartMessage(team_id='test_team_id', channel_id='test_channel_id', user_id='test_user_id', text='')],
    )


def test_queue_create_poll_with_text(mocked_sqs_v2):
    module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='1130 size=4',
        ),
        service_context,
    )

    service_context.clients.sqs_v2.send_messages.assert_called_with(
        'polls_to_start',
        [PollsToStartMessage(team_id='test_team_id', channel_id='test_channel_id', user_id='test_user_id', text='1130 size=4')],
    )


def test_queue_create_poll_help(mocked_sqs_v2):
    result = module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='help',
        ),
        service_context,
    )

    service_context.clients.sqs_v2.send_messages.assert_not_called()

    assert result == CREATE_POLL


def test_create_poll_fails_with_bad_text(mocked_sqs_v2):
    result = module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='foo bar',
        ),
        service_context,
    )

    service_context.clients.sqs_v2.send_messages.assert_not_called()

    assert result == 'Failed: Option could not be parsed into a time: "foo bar"'


def test_create_poll_fails_with_bad_text_size(mocked_sqs_v2):
    result = module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='foo bar size=a',
        ),
        service_context,
    )

    service_context.clients.sqs_v2.send_messages.assert_not_called()

    assert result == 'Failed: Size must be between 2 and 6. Received: "a"'


def test_create_poll_fails_with_bad_text_size_too_large(mocked_sqs_v2):
    result = module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='foo bar size=7',
        ),
        service_context.clients,
    )

    service_context.clients.sqs_v2.send_messages.assert_not_called()

    assert result == 'Failed: Size must be between 2 and 6. Received: "7"'
