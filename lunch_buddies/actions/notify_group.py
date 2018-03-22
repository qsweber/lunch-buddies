import random


def notify_group(message, slack_client, sqs_client, polls_dao, poll_responses_dao, teams_dao):
    team = teams_dao.read('team_id', message.team_id)[0]
    poll = polls_dao.find_by_callback_id(message.team_id, message.callback_id)
    choice = [
        choice
        for choice in poll.choices
        if choice.key == message.response
    ][0]

    user_in_charge = random.choice(message.user_ids)
    text = (
        'Hello! This is your lunch group for today. ' +
        'You all should meet somewhere at `{}`. '.format(choice.time) +
        'I am selecting <@{}> to be in charge of picking the location.'.format(user_in_charge)
    )

    conversation = slack_client.open_conversation(
        team=team,
        users=','.join(message.user_ids),
    )

    slack_client.post_message(
        team=team,
        channel=conversation['channel']['id'],
        as_user=True,
        text=text,
    )

    return True
