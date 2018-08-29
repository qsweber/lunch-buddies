from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants.help import CLOSE_POLL
from lunch_buddies.constants.queues import POLLS_TO_CLOSE, PollsToCloseMessage
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.types import ClosePoll


def queue_close_poll(request_form: ClosePoll, teams_dao: TeamsDao, sqs_client: SqsClient) -> str:
    if _is_help(request_form):
        return CLOSE_POLL

    message = PollsToCloseMessage(
        team_id=request_form.team_id,
        channel_id=request_form.channel_id,
        user_id=request_form.user_id,
    )

    sqs_client.send_message(
        POLLS_TO_CLOSE,
        message._asdict(),
    )

    return 'ok!'


def _is_help(request_form: ClosePoll) -> bool:
    return request_form.text.lower().strip() == 'help'
