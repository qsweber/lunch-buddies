from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants.help import CREATE_POLL
from lunch_buddies.constants.queues import POLLS_TO_START
from lunch_buddies.types import CreatePoll
import lunch_buddies.actions.queue_create_poll as module


def test_queue_create_poll(mocker):
    sqs_client = SqsClient()
    mocked_send_message = mocker.patch.object(
        sqs_client,
        'send_message',
        auto_spec=True,
        return_value=True,
    )

    module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='',
        ),
        sqs_client,
    )

    mocked_send_message.assert_called_with(
        POLLS_TO_START.queue_name,
        {'team_id': 'test_team_id', 'channel_id': 'test_channel_id', 'user_id': 'test_user_id', 'text': ''}
    )


def test_queue_create_poll_help(mocker):
    sqs_client = SqsClient()
    mocked_send_message = mocker.patch.object(
        sqs_client,
        'send_message',
        auto_spec=True,
        return_value=True,
    )

    result = module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='help',
        ),
        sqs_client,
    )

    mocked_send_message.assert_not_called()

    assert result == CREATE_POLL


def test_create_poll_fails_with_bad_text(mocker):
    sqs_client = SqsClient()
    mocked_send_message = mocker.patch.object(
        sqs_client,
        'send_message',
        auto_spec=True,
        return_value=True,
    )

    result = module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='foo bar',
        ),
        sqs_client,
    )

    mocked_send_message.assert_not_called()

    assert result == 'Failed: Option could not be parsed into a time: "foo bar"'


def test_create_poll_fails_with_bad_text_size(mocker):
    sqs_client = SqsClient()
    mocked_send_message = mocker.patch.object(
        sqs_client,
        'send_message',
        auto_spec=True,
        return_value=True,
    )

    result = module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='foo bar size=a',
        ),
        sqs_client,
    )

    mocked_send_message.assert_not_called()

    assert result == 'Failed: Size must be between 2 and 6. Received: "a"'


def test_create_poll_fails_with_bad_text_size_too_large(mocker):
    sqs_client = SqsClient()
    mocked_send_message = mocker.patch.object(
        sqs_client,
        'send_message',
        auto_spec=True,
        return_value=True,
    )

    result = module.queue_create_poll(
        CreatePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='foo bar size=7',
        ),
        sqs_client,
    )

    mocked_send_message.assert_not_called()

    assert result == 'Failed: Size must be between 2 and 6. Received: "7"'
