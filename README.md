# Lunch Buddies

![CI](https://github.com/qsweber/lunch-buddies/actions/workflows/pr.yml/badge.svg)

This is the backend for the Lunch Buddies Slack app. It's written in Go and follows the
patterns of [go-template](https://github.com/qsweber/go-template).

<!-- Points at the legacy Zappa API until cutover; switch to https://lunch-buddies-api.quinnweber.com/api/v0/install afterwards. -->
[![Add to Slack](https://platform.slack-edge.com/img/add_to_slack.png)](https://ahlfhssbq3.execute-api.us-west-2.amazonaws.com/production/api/v0/install)

## Architecture

The full design is in [docs/design/event-driven-single-table.md](docs/design/event-driven-single-table.md).
In short:

1. Slack calls the HTTP API (`cmd/apigateway`). Handlers only verify the request and write a
   row to a single DynamoDB table: a `REQUESTED` poll on create, a response on a button click,
   and `OPEN → CLOSED` on close.
2. A DynamoDB stream consumer (`cmd/dynamostream`) sees those two poll transitions and starts a
   Step Functions workflow.
3. **StartPoll** resolves the channel, opens the poll, and DMs each member (one `poll-user`
   task per user). **ClosePoll** forms the groups, saves them, and notifies each group (one
   `notify-group` task per group). Every task runs in the single `worker` Lambda, which
   dispatches on the payload's `task` field.

| Path | What |
| ---- | ---- |
| `cmd/apigateway`, `cmd/dynamostream`, `cmd/worker` | The three Lambdas: HTTP API, stream router, Step Functions tasks |
| `cmd/migrate` | One-off CLI that copies the legacy tables into the new table |
| `internal/polls` | Pure domain logic: parsing poll options, grouping, message text |
| `internal/repositories` | Single-table DynamoDB access (+ `memory/` for tests) |
| `internal/server` | HTTP routes |
| `internal/workflows` | Stream router and Step Functions task logic |
| `cdk/` | AWS CDK (Go) app; state machine definitions in `cdk/statemachines` |

## Data model

One table, `lunch-buddies-<env>-records`, with string keys `pk`/`sk` and one GSI (`gsi1`):

| Entity | pk | sk |
| ------ | -- | -- |
| Team | `TEAM#<team_id>` | `TEAM` |
| Active poll pointer | `TEAM#<team_id>` | `ACTIVE_POLL#<channel_id>` |
| Poll | `POLL#<callback_id>` | `POLL` |
| Recipient | `POLL#<callback_id>` | `RECIPIENT#<user_id>` |
| Response | `POLL#<callback_id>` | `RESPONSE#<user_id>` |
| Group | `POLL#<callback_id>` | `GROUP#<response_key>#<nnn>` |

## Development

Prerequisites: Go 1.25.8+. For deploys you also need Node.js 22+ and AWS credentials.

```bash
make test        # go test -race ./...
make vet
make fmt-check
make build       # builds every Lambda into dist/<name>.zip
```

## Deploy

Each stack reads its Slack settings from SSM Parameter Store String parameters at
`/lunch-buddies/<env>/<key>`. The keys are `slack_signing_secret`, `slack_verification_token`,
`slack_client_id`, `slack_client_secret` and `auth_url`. All five must exist before a deploy;
SSM can't store an empty value. To set them without echoing values or saving them to shell
history (use AWS CLI v2: v1 tries to download values that start with `https://`):

```bash
ENV=dev; for key in slack_signing_secret slack_verification_token slack_client_id slack_client_secret auth_url; do read -rsp "$key: " VALUE; echo; aws ssm put-parameter --region us-west-2 --type String --overwrite --name "/lunch-buddies/$ENV/$key" --value "$VALUE"; done; unset VALUE
```

CloudFormation resolves these only when it updates the Lambda, so after changing a value,
redeploy with a change to the function for it to take effect.

```bash
make build
cd cdk && npm ci
npx cdk diff lunch-buddies-dev
npx cdk deploy lunch-buddies-dev
```

CI (`.github/workflows`) runs tests and `cdk synth` on every pull request. Until the
production cutover, deploys only run by hand from the **Deploy** workflow.

## Why DynamoDB?

It costs nothing when idle and scales with usage. Running RDS would have meant paying for
uptime all day, every day.

## Credits

This app was inspired by https://github.com/monotkate/lunch-buddies
