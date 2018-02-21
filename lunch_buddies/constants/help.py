APP_EXPLANATION = '''
This is an app to help build relationships between members of a growing team. Each week, users will have the opportunity to join a small group of teammates for lunch. The `@lunch-buddies-bot` takes care of all of the logistics.

To initiate the process, simply run the `/lunch_buddies_create` command. This will send a message to each member of the #lunch-buddies channel asking if they want to participate. The possible answers are: "Yes (11:45)", "Yes (12:30)", and "No".

Once everyone has answered, a user should run the `/lunch_buddies_close` command. This will randomly group people by their answer and start a private group message for each group.

If you have any questions/comments/concerns/etc, please send an email to lunchbuddies@quinnweber.com
'''

CREATE_POLL = '`/lunch_buddies_create` Poll each member of the #lunch_buddies channel about participation. Once all responses have been received, run the /lunch_buddies_close command'

CLOSE_POLL = '`/lunch_buddies_close` Pull the responses to the latest poll and randomly group users based on their response.'
