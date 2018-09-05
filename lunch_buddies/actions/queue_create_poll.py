from lunch_buddies.actions.create_poll import parse_message_text, InvalidPollOption, InvalidPollSize
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.constants.help import CREATE_POLL
from lunch_buddies.constants.queues import POLLS_TO_START, PollsToStartMessage
from lunch_buddies.types import CreatePoll


def queue_create_poll(request_form: CreatePoll, sqs_client: SqsClient) -> str:
    if _is_help(request_form):
        return CREATE_POLL

    try:
        _validate(request_form)
    except (InvalidPollOption, InvalidPollSize) as e:
        return 'Failed: {}'.format(str(e))

    message = PollsToStartMessage(
        team_id=request_form.team_id,
        channel_id=request_form.channel_id,
        user_id=request_form.user_id,
        text=request_form.text,
    )

    sqs_client.send_message(
        POLLS_TO_START,
        message._asdict(),
    )

    return 'ok!'


def _is_help(request_form: CreatePoll) -> bool:
    return request_form.text.lower().strip() == 'help'


def _validate(request_form: CreatePoll) -> bool:
    text = request_form.text

    parse_message_text(text)

    return True
