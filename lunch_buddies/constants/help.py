from lunch_buddies.constants.polls import DEFAULT_GROUP_SIZE

TAG_LINE_SHORT = 'Meet random teammates for lunch'

TAG_LINE = 'Builds relationships between teammates by coordinating random lunch groups.'

CREATE_POLL = (
  'To initiate the process, invite the Lunch Buddies bot to any channel and ' +
  'say `@Lunch Buddies create`. This will send a message to each member of the current channel ' +
  'asking if they want to participate.' +
  '\n\n' +
  'The default options are: `Yes (12:00)`, and `No`, but you can customize by saying `@Lunch Buddies create 1145, 1230`.' +
  '\n\n' +
  'The default group size is {}, but this can be customize by saying `@Lunch Buddies create 1145, 1230 size=4`'.format(DEFAULT_GROUP_SIZE) +
  '\n\n' +
  'You can also create polls using the legacy `/lunch_buddies_create` slash command. ' +
  'Regardless of where this command is invoked, it will poll the members of the `#lunch_buddies` channel. ' +
  '\n\n' +
  'It is possible to have multiple polls going at the same time; they are uniquely defined by the channel from which they were created. '
)

CLOSE_POLL = (
  'Once everyone has answered, go back to the same channel from which the poll was created ' +
  'and write `@Lunch Buddies close`. This will randomly group the responders by their answer ' +
  'and start a private group message for each group. ' +
  '\n\n' +
  'If you created the poll with the slash command `/lunch_buddies_create`, you should close it with the slash command `/lunch_buddies_close`.'
)

SUPPORT_LINE = 'If you have any questions, comments or concerns, please send an email to support@lunchbuddiesapp.com'

APP_EXPLANATION = '{}\n\n{}\n\n{}\n\n{}'.format(
  TAG_LINE,
  CREATE_POLL,
  CLOSE_POLL,
  SUPPORT_LINE,
)
