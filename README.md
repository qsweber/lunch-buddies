# Lunch Buddies

![CI](https://github.com/qsweber/lunch-buddies/workflows/CI/badge.svg) [![Coverage Status](https://coveralls.io/repos/github/qsweber/lunch-buddies/badge.svg?branch=master)](https://coveralls.io/github/qsweber/lunch-buddies?branch=master) [![Type Coverage](https://img.shields.io/badge/mypy-66-red)]

Slack APP for creating lunch buddy groups.

[![Add to Slack](https://platform.slack-edge.com/img/add_to_slack.png)](https://ahlfhssbq3.execute-api.us-west-2.amazonaws.com/production/api/v0/install)

## How it works

This is a python flask app that has the following entrypoints.

### Workflow

#### create_poll_http

This is exposed to the web, and is invoked via a slash command. When this function is called, a message is added to the `polls_to_create` SQS queue with information about the poll that needs creation.

#### create_poll_from_queue

This is a CRON job that runs every 5 minutes and tries to read from the `polls_to_create` queue. When a message is found, it does the following:

- Save a `Poll` object to DynamoDB
- Find all of the users in the `lunch_buddies` channel
- For each user, write a message to the `users_to_poll` queue

#### poll_users_from_queue

This is a CRON job that runs every 5 minutes and tries to read from the `users_to_poll` queue. When a message is found, it does the following:

- Send a direct message to the user with a question about participating in "Lunch Buddies"

#### listen_to_poll_http

This is exposed to the web and is invoked when a clicks on a button in the message sent in the `poll_users_from_queue` step. When a user clicks on a button, a POST request is made to this endpoint and the following happens:

- Saves information as a `PollResponse` object in DynamoDB

#### close_poll_http

This is exposed to the web, and is invoked via a slash command. When this function is called, a message is added to the `polls_to_close` SQS queue with information about the poll that needs to be closed.

#### close_poll_from_queue

This is a CRON job that runs every 5 minutes and tries to read from the `polls_to_close` queue. When a message is found, it does the following:

- Find the most recent `Poll` for in DynamoDB
- Get all of the `PollResponse` objects for that poll
- Randomly group respondants
- For each group of respondants, write to the `groups_to_notify` queue 

#### close_poll_from_queue

This is a CRON job that runs every 5 minutes and tries to read from the `groups_to_notify` queue. When a message is found, it does the following:

- Send a private group message to the group of users that should meet
- Randomly select one of the users to choose where to meet

### Other Development notes

This is entirely serverless and uses a combination of Lambda, SQS, and DynamoDB. Continuous deployment happens with TravisCI.

## Credits

This App was inspired by https://github.com/monotkate/lunch-buddies
