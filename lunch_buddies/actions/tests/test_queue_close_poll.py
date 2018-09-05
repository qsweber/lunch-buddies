from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants.queues import POLLS_TO_CLOSE
from lunch_buddies.constants.help import CLOSE_POLL
from lunch_buddies.types import ClosePoll
import lunch_buddies.actions.queue_close_poll as module


def test_queue_close_poll(mocker):
    sqs_client = SqsClient()
    mocked_send_message = mocker.patch.object(
        sqs_client,
        'send_message',
        auto_spec=True,
        return_value=True,
    )

    module.queue_close_poll(
        ClosePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='',
        ),
        sqs_client,
    )

    mocked_send_message.assert_called_with(
        POLLS_TO_CLOSE,
        {'team_id': 'test_team_id', 'channel_id': 'test_channel_id', 'user_id': 'test_user_id'}
    )


def test_queue_close_poll_help(mocker):
    sqs_client = SqsClient()
    mocked_send_message = mocker.patch.object(
        sqs_client,
        'send_message',
        auto_spec=True,
        return_value=True,
    )

    result = module.queue_close_poll(
        ClosePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='help',
        ),
        sqs_client,
    )

    mocked_send_message.assert_not_called()

    assert result == CLOSE_POLL
