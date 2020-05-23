# Lunch Buddies

![CI](https://github.com/qsweber/lunch-buddies/workflows/CI/badge.svg) ![Test Coverage](https://img.shields.io/badge/tests-86%25-yellow) ![Type Coverage](https://img.shields.io/badge/types-67%25-red)

This is the backend for the Lunch Buddies slack app.

[![Add to Slack](https://platform.slack-edge.com/img/add_to_slack.png)](https://ahlfhssbq3.execute-api.us-west-2.amazonaws.com/production/api/v0/install)

## Basic Architecture

### Flow of information

![Architecture Diagram](https://github.com/qsweber/lunch-buddies/blob/readme-media/media/architecture.png)

The above diagram shows the flow of information throughout the system. The diagram shows two Lambda functions. The one on the left is running a flask app and responding to HTTP requests. The one on the left is an async task handler triggered by messages being added to one of the SQS queues.

1. The flask app receives a request from slack to start a poll and adds a message to the "polls_to_start" queue.
2. The presence of a message in the "polls_to_start" queue triggers a task that finds which users to notify and adds a message per user to the "users_to_poll" queue.
3. The presence of a message in the "users_to_poll" queue triggers a task that sends a message to the user asking about participation.
4. Each user clicks an option on the poll, which is handled by the flask app. Responses are stored in DynamoDB.
5. When it's time to close the poll and aggregate results, a user triggers this within Slack, which pings the flask app, which adds a message to the "polls_to_close" queue.
6. A message in the "polls_to_close" queue triggers a task that gathers all responses and divides respondants into evenly sized groups. A message per group is added to the "groups_to_notify" queue.
7. A message in the "groups_to_notify" queue triggers a task that notifies the group in slack

### Why so many queues?

When user interactions are sent to the flask app, Slack expects a response within 3 seconds. Most of the operations that need to happen as a result of the user interaction could take longer than 3 seconds, so I figured it was safer to put as much as possible into the async handlers.

### Database schema

![Database Schema](https://github.com/qsweber/lunch-buddies/blob/readme-media/media/database.png)

### Why DynamoDB for a relational database?

When I first started building this app, I wanted to make it as cheap as possible to run. DynamoDB scales really well, and I only have to pay for usage. Using RDS would have meant paying for uptime all day every day.

### What's up with those Primary Keys?

DynamoDB only really supports having a primary key, and that key can either be one column or two. If two, the second column is called the "sort key".

In the case of the "polls" table, I had to build the keys around the usage pattern, which was that I'd be receiving a user input from a specific team to open or close a poll. I needed to be able to look up the polls for that team, which meant team_id had to be in the primary key. Since team_id does not uniquely define a poll, I picked "created_at" for the sort key.

## Other technologies used

- Zappa
- Github Actions
- Stripe

## Credits

This App was inspired by https://github.com/monotkate/lunch-buddies
