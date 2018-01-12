
def _poll_users(slack_client):
    # users = slack_client.list_users()
    # for user in users:
    #     # user = slack_client.list_users()[2]
    #     slack_client.post_message(
    #         channel=user['id'],
    #         text='Are you able to participate in Lunch Buddies today?',
    #         attachments=[
    #             {
    #                 'text': 'Are you able to participate in Lunch Buddies today?',
    #                 'fallback': 'Something has gone wrong.',
    #                 'callback_id': 'participating',
    #                 'color': '#3AA3E3',
    #                 'attachment_type': 'default',
    #                 'actions': [
    #                     {
    #                         'name': 'answer',
    #                         'text': 'Yes (11:45)',
    #                         'type': 'button',
    #                         'value': 'yes_0'
    #                     },
    #                     {
    #                         'name': 'answer',
    #                         'text': 'Yes (12:30)',
    #                         'type': 'button',
    #                         'value': 'yes_1'
    #                     },
    #                     {
    #                         'name': 'answer',
    #                         'text': 'No',
    #                         'type': 'button',
    #                         'value': 'no'
    #                     },
    #                 ],
    #             },
    #         ]
    #     )
    pass


def poll_listener(incoming_message):
    pass
