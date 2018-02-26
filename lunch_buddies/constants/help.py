TAG_LINE = 'This app helps build relationships between members of a growing team. Each week, users will have the opportunity to join a small group of teammates for lunch. The @lunch_buddies_bot takes care of all the logistics.'

CREATE_POLL = 'To initiate the process, run the `/lunch_buddies_create` command. This will send a message to each member of the #lunch-buddies channel asking if they want to participate. The default possible answers are: "Yes (12:00)", and "No". You may also specify a set of custom times. For example, "/lunch_buddies_create 1145, 1230" will create a poll whose possible answers are "Yes (11:45)", "Yes (12:30)" and "No". You do not need to explicitly set "no" as an option; it is included by default.'

CLOSE_POLL = 'Once everyone has answered, a user should run the `/lunch_buddies_close` command. This will randomly group people by their answer and start a private group message for each group.'

SUPPORT_LINE = 'If you have any questions/comments/concerns/etc, please send an email to lunchbuddies@quinnweber.com'

APP_EXPLANATION = '{}\n\n{}\n\n{}\n\n{}'.format(
  TAG_LINE,
  CREATE_POLL,
  CLOSE_POLL,
  SUPPORT_LINE,
)
