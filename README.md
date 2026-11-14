# Lunch Buddies

![CI](https://github.com/qsweber/lunch-buddies/actions/workflows/pr.yml/badge.svg)

This is the backend for the Lunch Buddies Slack app. It's written in Go and follows the
patterns of [go-template](https://github.com/qsweber/go-template).

<!-- Points at the legacy Zappa API until cutover; switch to https://api.lunchbuddiesapp.com/v1/install afterwards. -->
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
| `cmd/migrate` | One-off cutover CLI: copies teams from the legacy table, and refuses to run while a legacy poll is in flight |
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

## Install URL and OAuth scopes

`/v1/install` redirects to Slack's authorize page, built in code from the `BotScopes` list in
`internal/server/auth.go`, the `slack_client_id` parameter and the redirect URI
`<API_BASE_URL>/v1/auth`. `API_BASE_URL` is set by CDK from the stack's domain. When you change
scopes, change them in the Slack app (OAuth & Permissions → Bot Token Scopes) and in `BotScopes`
together. The redirect URI must be listed under the app's Redirect URLs.

## Slack app event subscriptions

Under **Event Subscriptions → Subscribe to bot events**, the app needs `app_mention` (commands),
plus `app_uninstalled` and `tokens_revoked`, so uninstalls are recorded and dead tokens deleted.
None of these needs an extra scope.

## Deploy

The API Lambda reads its Slack settings from SSM Parameter Store at
`/lunch-buddies/<env>/<key>` when it cold-starts (String or SecureString both work). The keys are
`slack_signing_secret`, `slack_verification_token`, `slack_client_id` and `slack_client_secret`.
All four must exist, or the API fails to start (the deploy's ping check catches this); SSM can't
store an empty value. To set them without echoing values or saving them to shell history:

```bash
# zsh (macOS default)
ENV=dev; for key in slack_signing_secret slack_verification_token slack_client_id slack_client_secret; do read -rs "VALUE?$key: "; echo; aws ssm put-parameter --region us-west-2 --type SecureString --overwrite --name "/lunch-buddies/$ENV/$key" --value "$VALUE"; done; unset VALUE
```

In bash, use `read -rsp "$key: " VALUE` instead of `read -rs "VALUE?$key: "`.

A changed value takes effect when the API Lambda next cold-starts; no redeploy is needed.
To make it take effect immediately, recycle the running instances:

```bash
aws lambda update-function-configuration --region us-west-2 --function-name lunch-buddies-dev-api --description "settings reloaded $(date -u +%FT%TZ)"
```

```bash
make build
cd cdk && npm ci
npx cdk diff lunch-buddies-dev
npx cdk deploy lunch-buddies-dev
```

CI follows go-template's workflows: `pr.yml` runs tests and `cdk synth` on every pull request
and deploys the dev stack, and `production.yml` deploys prod on every push to `master`. Both
call the shared `ci.yml`, which refuses to update a stack this app didn't create.

During the production cutover, the API can forward every Slack request to the legacy Zappa
API: set `/lunch-buddies/<env>/legacy_forward_url` to its base URL, then recycle the Lambda
(command above). Delete the parameter and recycle again to serve requests directly. See the
design doc §8.3 and §8.5.

`go run ./cmd/migrate -target lunch-buddies-prod-records` (a dry run by default) checks the
legacy table for polls in flight and reports how many teams it would copy; see design doc §8.4.

## Why DynamoDB?

It costs nothing when idle and scales with usage. Running RDS would have meant paying for
uptime all day, every day.

## Credits

This app was inspired by https://github.com/monotkate/lunch-buddies
