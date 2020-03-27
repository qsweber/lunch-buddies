from lunch_buddies.lib.service_context import service_context
from lunch_buddies.constants.help import CLOSE_POLL
from lunch_buddies.types import ClosePoll, PollsToCloseMessage
import lunch_buddies.actions.queue_close_poll as module


def test_queue_close_poll(mocked_sqs_v2):
    module.queue_close_poll(
        ClosePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='',
        ),
        service_context,
    )

    service_context.clients.sqs_v2.send_messages.assert_called_with(
        'polls_to_close',
        [PollsToCloseMessage(team_id='test_team_id', channel_id='test_channel_id', user_id='test_user_id')],
    )


def test_queue_close_poll_help(mocked_sqs_v2):
    result = module.queue_close_poll(
        ClosePoll(
            team_id='test_team_id',
            channel_id='test_channel_id',
            user_id='test_user_id',
            text='help',
        ),
        service_context,
    )

    service_context.clients.sqs_v2.send_messages.assert_not_called()

    assert result == CLOSE_POLL
