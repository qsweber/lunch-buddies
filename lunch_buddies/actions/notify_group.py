import random


def notify_group(message, slack_client, sqs_client, polls_dao, poll_responses_dao):
    hourminute = message['response'].split('_')[1]
    hourminute_formatted = '{}:{}'.format(hourminute[0:2], hourminute[2:4])

    user_in_charge = random.choice(message['user_ids'])
    text = (
        'Hello! This is your lunch group for today. ' +
        'You all should meet somewhere at `{}`. '.format(hourminute_formatted) +
        'I am selecting <@{}> to be in charge of picking the location.'.format(user_in_charge)
    )

    conversation = slack_client.open_conversation(users=','.join(message['user_ids']))

    slack_client.post_message(
        channel=conversation['channel']['id'],
        text=text,
    )

    return True
