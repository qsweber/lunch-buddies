# 2020-02-25

Fixed a bug that was caused by the slack api deprecating. See [here](https://api.slack.com/changelog/2020-01-deprecating-antecedents-to-the-conversations-api) for more information.

Users would attempt to create a poll in a private channel. On the first attempt, they would successfully get past the "active poll" check and create a new row in the polls table. After creating the database entity, the code would attempt to list the users in the provided channel. This would fail due to the deprecated groups.info method. Upon the second attempt to handle the SQS message, the code would see there was already an "active poll" in the channel and send an error message to the user.

If DynamoDB supported transactions, this would be more avoidable.