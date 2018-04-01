TAG_LINE = 'This app helps build relationships between members of a growing team. Each week, users will have the opportunity to join a small group of teammates for lunch. The `@lunch_buddies_bot` takes care of all the logistics.'

CREATE_POLL = 'To initiate the process, invite @lunch_buddies_bot to a channel and say `@lunch_buddies_bot create`. This will send a message to each member of the current channel asking if they want to participate.\n\nThe default possible answers are: `Yes (12:00)`, and `No`. You may also specify a set of custom times. For example, `@lunch_buddies_bot create 1145, 1230` will create a poll whose possible answers are `Yes (11:45)`, `Yes (12:30)` and `No`. You do not need to explicitly set `no` as an option; it is included by default.\n\nYou may also use the `/lunch_buddies_create` command. This slash command can be invoked from anywhere in slack and it will poll the members of the `#lunch_buddies` channel. This is the legacy way of creating a poll.\n\nIt is possible to have multiple polls going at the same time; they are uniquely defined by the channel from which they were created. For example, you can go to the #seattle_office channel and say `@lunch_buddies_bot create`, and then go right to the #san_francisco_office channel and say `@lunch_buddies_bot create`. Members of each channel will be independently polled and grouped.'

CLOSE_POLL = 'Once everyone has answered, you should go back to the same channel from which the poll was created and write `@lunch_buddies_bot close`. This will randomly group the responders by their answer and start a private group message for each group. For example, if 60 people said `Yes (11:45)` and 30 people said `Yes (12:30)`, @lunch_buddies_bot will create 10 random groups for the 11:45 time and 5 random groups for the 12:30 time.\n\nIf you created the poll with the slack command `/lunch_buddies_create`, you should close it with the slash command `/lunch_buddies_close`.'

SUPPORT_LINE = 'If you have any questions/comments/concerns/etc, please send an email to lunchbuddies@quinnweber.com'

APP_EXPLANATION = '{}\n\n{}\n\n{}\n\n{}'.format(
  TAG_LINE,
  CREATE_POLL,
  CLOSE_POLL,
  SUPPORT_LINE,
)
