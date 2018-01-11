from lunch_buddies.clients import slack


MESSAGE = {
    "text": "Are you able to participate in Lunch Buddies today?",
    "attachments": [
        {
            "text": "Are you able to participate in Lunch Buddies today?",
            "fallback": "Something has gone wrong.",
            "callback_id": "participating",
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": [
                {
                    "name": "answer",
                    "text": "Yes (11:45)",
                    "type": "button",
                    "value": "yes_0"
                },
                {
                    "name": "answer",
                    "text": "Yes (12:30)",
                    "type": "button",
                    "value": "yes_1"
                },
                {
                    "name": "answer",
                    "text": "No",
                    "type": "button",
                    "value": "no"
                },
            ],
        },
    ],
}


def poll_users():
    users = slack.get_all_users()

    for user in users:
        slack.send_message()


def poll_listener(response):
    # write the results to a database
    pass
