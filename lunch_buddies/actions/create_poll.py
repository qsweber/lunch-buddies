from datetime import datetime
import uuid

from lunch_buddies.constants import polls, slack
from lunch_buddies.constants.queues import USERS_TO_POLL, UsersToPollMessage
from lunch_buddies.models.polls import Poll, ChoiceList, Choice


def create_poll(message, slack_client, sqs_client, polls_dao, poll_responses_dao, teams_dao):
    team = teams_dao.read('team_id', message.team_id)[0]
    poll = polls_dao.find_latest_by_team_id(message.team_id)

    if poll and poll.state != polls.CLOSED:
        slack_client.post_message(
            team=team,
            channel=message.user_id,
            as_user=True,
            text='There is already an active poll',
        )

        return True

    callback_id = _get_uuid()
    created_at = _get_created_at()

    if message.text:
        choices = get_choices_from_message_text(message.text)
    else:
        choices = polls.CHOICES  # TODO figure this out

    poll = Poll(
        team_id=message.team_id,
        created_at=created_at,
        created_by_user_id=message.user_id,
        callback_id=callback_id,
        state=polls.CREATED,
        choices=choices,
    )

    polls_dao.create(poll)

    users_to_poll = [
        user
        for user in slack_client.list_users(team, slack.LUNCH_BUDDIES_CHANNEL_NAME)
        if user['is_bot'] is False and user['name'] != 'slackbot'
    ]
    for user in users_to_poll:
        outgoing_message = {'team_id': message.team_id, 'user_id': user['id'], 'callback_id': callback_id}
        sqs_client.send_message(
            USERS_TO_POLL,
            UsersToPollMessage(**outgoing_message),
        )

    return True


def _get_uuid():
    return uuid.uuid4()


def _get_created_at():
    return datetime.now()


class InvalidPollOption(Exception):
    def __init__(self, option):
        super(InvalidPollOption, self).__init__(
            'Option could not be parsed into a time: "{}"'.format(option)
        )


def get_choices_from_message_text(text):
    # TODO: first argument can be a channel?

    options = list(map(lambda o: o.strip(), text.split(',')))

    choices = list(map(get_choice_from_raw_option, options))
    choices.append(Choice(
        key='no',
        is_yes=False,
        time='',
        display_text='No',
    ))

    return ChoiceList(choices)


def get_choice_from_raw_option(option):
    try:
        int(option)
    except ValueError:
        raise InvalidPollOption(option)

    time = get_time_from_raw_option(option)

    return Choice(
        key='yes_{}'.format(option),
        is_yes=True,
        time=time,
        display_text='Yes ({})'.format(time),
    )


def get_time_from_raw_option(raw_option):
    hour = int(raw_option[:-2])
    minute = int(raw_option[-2:])

    try:
        datetime(2018, 1, 1, hour, minute)
    except ValueError:
        raise InvalidPollOption(raw_option)

    return '{}:{}'.format(hour, str(minute).zfill(2))
