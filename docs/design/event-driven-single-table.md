# Lunch Buddies backend: event-driven, single-table rewrite in Go

Status: **Implemented on this branch, not yet deployed** (rev 4; rev 1 was Python, rev 2 was the Go design before implementation, rev 3 recorded implementation learnings)
Base commit: `2aa093f` · Template reference: `qsweber/go-template@8ad5afe`

Changes from rev 2, learned while implementing, are marked **[rev 3]**. Review follow-ups are marked **[rev 4]**.

## 1. Goals

1. **Rewrite the backend in Go**, following the patterns in [`go-template`](https://github.com/qsweber/go-template). Flask, Zappa and the Python codebase are retired. **[rev 3]** All Python is removed in this PR rather than at decommission (§8).
2. **The HTTP layer only writes state.** Each Slack request does a small number of DynamoDB reads/writes and returns right away. It never fans out and never calls Slack, except to reply inline.
3. **One DynamoDB table** (single-table design, template conventions) replaces `lunch_buddies_Team`, `_Poll`, `_PollResponse` and `_Group`.
4. **State changes drive the work.** A DynamoDB Streams consumer watches for poll state *transitions* and starts a Step Functions workflow for each one.
5. **Fan-out runs in Step Functions**, not by chaining SQS queues. There is one Lambda task per user (send the poll DM) and one per group (send the group message).
6. Fix the correctness gaps the current design can't handle well (see §2.2).

Non-goals: changing the poll UX, the grouping algorithm or the OAuth flow. They are **ported as-is**; behaviour parity is the bar.

**[rev 4]** Invoicing and Stripe are **removed**, not ported (never used in practice, see §5.4). The five Step Functions tasks run in **one `worker` Lambda** (§3.1).

## 2. Current state (summary)

### 2.1 Flow today

```
Slack ──► Flask (Zappa Lambda) ──► SQS polls_to_start ──► create_poll  ──► SQS users_to_poll ──► poll_user ──► Slack DM
Slack ──► Flask: button click ───────────────────────────► PollResponse table
Slack ──► Flask ──► SQS polls_to_close ──► close_poll ──► SQS groups_to_notify ──► notify_group ──► Slack
```

### 2.2 Problems this design fixes

| # | Problem | Where (Python today) | How the new design fixes it |
|---|---------|----------------------|---------------------|
| P1 | **Race on "one active poll per channel"**: it's a read-then-write. | `create_poll.py` | A conditional `ACTIVE_POLL` pointer item, written in a transaction (§4.3). |
| P2 | **Looking up a poll by `callback_id` reads every poll the team has ever made.** | `PollsDao.find_by_callback_id_or_die` | `pk = POLL#<callback_id>` → a single `GetItem`. |
| P3 | **Responses are accepted after a poll closes**, but never grouped. | `listen_to_poll.py` | The response write includes a `ConditionCheck` that the poll is `OPEN`. |
| P4 | **Non-idempotent retries**: double DMs, re-shuffled groups, half-created polls. | `create_poll`, `close_poll`, `notify_group` | Every workflow step is idempotent (§6). |
| P5 | `time.sleep(1)` per DM as a rate limiter. | `poll_user.py` | Map `MaxConcurrency` + Retry on `RateLimitedError`. |
| P6 | Slack Events API retries are not deduped. | `bot_http` | Requests with `X-Slack-Retry-Num` are acknowledged without acting. |
| P7 | Close errors come back as async DMs. | `close_poll.py` | Close replies inline. |
| P8 | The API URL is a raw `execute-api` hostname. | Zappa | A custom domain (template `cdk/domain.go`). |
| P9 **[rev 3]** | **Secrets in logs.** `oauth2.py:41` logs the full OAuth response, including the bot `access_token`. `bot.py:102` logs the raw request, including the legacy verification token. Log groups never expire. | Python | The Go code never logs either one. Every Lambda gets an explicit log group with 90-day retention. |

## 3. Target architecture

```mermaid
flowchart LR
    Slack((Slack))
    subgraph API["cmd/apigateway (HTTP API v2)"]
      create["/poll/create, /bot create"]
      respond["/poll (button click)"]
      close["/poll/close, /bot close"]
    end
    DDB[(lunch-buddies-&lt;env&gt;-records)]
    Stream{{DynamoDB Stream<br/>NEW_AND_OLD_IMAGES}}
    Router["cmd/dynamostream<br/>(filtered ESM + DLQ)"]
    subgraph SFN1["StartPoll (tasks run in cmd/worker)"]
      v[prepare-poll] --> m1[[Map: poll-user]]
    end
    subgraph SFN2["ClosePoll (tasks run in cmd/worker)"]
      g[form-groups] --> m2[[Map: notify-group]] --> done[MarkPollComplete<br/>native DynamoDB task]
    end

    Slack --> create & respond & close
    create -- "PutItem POLL state=REQUESTED" --> DDB
    respond -- "TransactWrite: Put RESPONSE + ConditionCheck POLL=OPEN" --> DDB
    close -- "TransactWrite: POLL OPEN→CLOSED, delete ACTIVE_POLL" --> DDB
    DDB --> Stream --> Router
    Router -- "INSERT state=REQUESTED" --> SFN1
    Router -- "MODIFY OPEN→CLOSED" --> SFN2
    m1 -- "DM per user" --> Slack
    m2 -- "message per group" --> Slack
```

### 3.1 Components

| `cmd/…` | Lambda function | Trigger | Logic lives in |
|---------|-----------------|---------|----------------|
| `apigateway` | `<stack>-api` | HTTP API v2 `$default` route | `internal/server` |
| `dynamostream` | `<stack>-stream-router` | DynamoDB stream ESM with filter criteria, DLQ | `internal/workflows/router.go` |
| `worker` | `<stack>-worker` | Every Step Functions task | `internal/workflows` (`worker.go` dispatches) |
| `migrate` | – (local CLI) | Run by hand at cutover | `internal/migrate` |

**[rev 4] One worker Lambda for all Step Functions tasks.**
- Every task payload carries a `task` field (`prepare-poll`, `poll-user`, `form-groups`, `notify-group`, `notify-failure`). `workflows.Deps.Handle` unmarshals the input for that task and calls it.
- Errors are returned unwrapped, so the `RateLimitedError` Retry match still works.
- Only two Lambdas stay separate, because their trigger, payload shape and IAM genuinely differ:
  - The API is called by API Gateway. It has reserved concurrency and the Slack secrets.
  - The router gets stream batches and is the only role allowed `states:StartExecution`.
- The tasks shared a trigger, role, timeout and environment anyway. Per-task debugging comes from the execution history, which names the failing state. One function also shares warm instances across tasks.
- This still follows go-template's one-`cmd`-per-Lambda convention. What changed is how many Lambdas there are: one function now handles several Step Functions tasks, where the template's Lambdas each do one job.
- **Rule for new code:** one Lambda per `cmd`, and one `cmd` per ingress type: HTTP (`apigateway`), the DynamoDB stream (`dynamostream`) and Step Functions tasks (`worker`). A new Step Functions task is a new `task` case in `worker`, not a new `cmd`. A new `cmd` is only for a new kind of trigger, such as an EventBridge schedule or SQS.

Infrastructure is CDK in Go under `cdk/`, written in the template's L1 `Cfn*` style. The state machines are `cdk/statemachines/*.asl.json` with `DefinitionSubstitutions`.

**[rev 3] Runtime:** `provided.al2023`. The template's `provided.al2` reached end of support with Amazon Linux 2 in mid-2026, so the template should move too.

**[rev 3] Go version:** Go 1.25.8, as in the template. `aws-lambda-go` is pinned to v1.47.0 because v1.55+ requires Go 1.26.

## 4. Data model (single table)

The table is `lunch-buddies-<env>-records`, with string keys `pk`/`sk` and one GSI, `gsi1` (`gsi1pk`/`gsi1sk`). Entities are distinguished by key shape. Timestamps are Unix milliseconds. Stream view is `NEW_AND_OLD_IMAGES`. PITR is on, the table is retained on stack delete, and prod has deletion protection.

### 4.1 Items

| Entity | pk | sk | gsi1pk | gsi1sk | Other attributes |
|--------|----|----|--------|--------|------------------|
| Team | `TEAM#<team_id>` | `TEAM` | – | – | `bot_access_token` (plaintext, see §12), `name`, `created_at`, `feature_notify_in_channel` |
| ActivePoll pointer | `TEAM#<team_id>` | `ACTIVE_POLL#<channel_id>` | – | – | `callback_id`, `created_at` |
| Poll | `POLL#<callback_id>` | `POLL` | `TEAM#<team_id>` | `POLL#<created_at, 13-digit>` | `state`, `channel_id`, `created_by_user_id`, `choices`, `group_size`, `requested_text`, `rejection_reason`, `closed_by_user_id`, `closed_at`, **`group_count` [rev 3]** |
| Recipient | `POLL#<callback_id>` | `RECIPIENT#<user_id>` | – | – | `sent_at`, `message_ts` |
| PollResponse | `POLL#<callback_id>` | `RESPONSE#<user_id>` | – | – | `response`, `created_at` |
| Group | `POLL#<callback_id>` | `GROUP#<response_key>#<nnn>` (migrated: `#m<hash>`) | – | – | `user_ids`, `response_key`, `notified_at` |

**Why the ActivePoll pointer is its own row:** DynamoDB conditions only apply to the item being written. "At most one open poll per channel" is a rule across items, and the only way to enforce it atomically is a row keyed by the rule itself. The pointer also makes "the open poll in this channel" a single strongly consistent `GetItem` for close.

**[rev 3] Repository shape.** There is one `PollsRepository` for the whole poll item collection plus the pointers, rather than one repository per entity as in the template. The important operations (`OpenPoll`, `ClosePoll`, `RecordResponse`, `SaveGroups`) are transactions spanning several entity types, so splitting them would scatter that logic. Teams keep their own `TeamsRepository`.

### 4.2 Access patterns

| # | Pattern | Operation |
|---|---------|-----------|
| A1 | Get team | `GetItem TEAM#t / TEAM` |
| A2 | Get poll | `GetItem POLL#c / POLL` (strongly consistent) |
| A3 | Active poll for channel | `GetItem TEAM#t / ACTIVE_POLL#ch` |
| A4 | All active polls for team | `Query TEAM#t, begins_with(sk, "ACTIVE_POLL#")` |
| A5 | Poll + children | `Query POLL#c` (strongly consistent) |
| A6 | Team's polls since date (summary) | `Query gsi1 TEAM#t, gsi1sk BETWEEN …` |

**[rev 4]** The "all teams" GSI partition (`gsi1pk = TEAMS`) existed only for invoicing and was removed. GSI1 now indexes polls only.

### 4.3 Poll state machine

```
            (API)                 (prepare-poll)             (API close)          (MarkPollComplete)
  ∅ ──► REQUESTED ──────────────► OPEN ────────────────────► CLOSED ────────────► COMPLETE
             │
             └──(prepare-poll)──► REJECTED   (no default channel / user not in channel / active poll exists)
```

- `REQUESTED → OPEN`: one transaction that updates the poll (condition `state = REQUESTED`) and puts the pointer (condition `attribute_not_exists(pk) OR created_at < now-24h`). The cancellation reason tells us which condition failed: `ErrInvalidTransition` or `ErrActivePollExists`.
- `OPEN → CLOSED`: one transaction that updates the poll (condition `state = OPEN`) and deletes the pointer (condition `callback_id = :c`).
- **[rev 3]** Groups are written in one transaction together with `SET group_count` on the poll (condition `state = CLOSED AND attribute_not_exists(group_count)`). That makes "groups formed" all-or-nothing: a retry finds every group or none, so it never re-shuffles and never sees a partial set. TransactWriteItems allows 100 items, so a poll can have **at most 99 groups** (about 600 "yes" respondents at the default size). Beyond that, `FormGroups` fails loudly.

Stream filter criteria (in `cdk/stream.go`) pass only these two transitions; the router re-checks them in code:

```json
{"eventName":["INSERT"],"dynamodb":{"NewImage":{"sk":{"S":["POLL"]},"state":{"S":["REQUESTED"]}}}}
{"eventName":["MODIFY"],"dynamodb":{"OldImage":{"state":{"S":["OPEN"]}},"NewImage":{"sk":{"S":["POLL"]},"state":{"S":["CLOSED"]}}}}
```

## 5. Flows

### 5.0 HTTP handling

- **[rev 4]** Routes are under `/v1/` (`/v1/poll/create`, `/v1/poll`, `/v1/poll/close`, `/v1/help`, `/v1/install`, `/v1/auth`, `/v1/bot`, `/v1/ping`), matching go-template. The Python app's `/api/v0/...` paths weren't kept: the host changes at cutover anyway, so every Slack URL is re-entered regardless.
- **Verification** (`internal/slackverify`): the v0 HMAC signature with the signing secret, with a 5-minute clock skew window. A request without a signature is accepted if it carries the legacy verification token. A request *with* a signature must pass the signature check; a valid legacy token doesn't rescue a bad signature.
- `/bot` answers `url_verification` and ignores `X-Slack-Retry-Num` retries.

### 5.1 Create

1. The API verifies the request and the team, handles `help`, parses the text (`Failed: …` inline on error), and does `PutItem` with `REQUESTED`. It replies `ok!`.
2. The router starts `StartPoll` with execution name `start-<callback_id>`.
3. `prepare-poll`:
   - For the slash command (no channel), resolve `#lunch_buddies` and check the creator is a member.
   - Then do `OpenPoll`.
   - On any rejection, DM the creator and mark the poll `REJECTED`.
   - Return the channel members.
4. Map, `MaxConcurrency` 5: `poll-user`.
   - **[rev 3] `prepare-poll` no longer bulk-writes recipient rows.** BatchWriteItem can't be conditional, so a re-run would overwrite `sent_at`.
   - Instead, `poll-user` checks for a recipient row, sends the DM, then writes the row with `sent_at`.
   - A failed user is caught and skipped, so one deactivated account doesn't fail the poll.

### 5.2 Respond

`GetPoll` → `TransactWrite(ConditionCheck OPEN, Put RESPONSE)` → return the original message plus a confirmation. If the condition failed: "This poll has already closed, so your answer was not recorded."

### 5.3 Close

1. The API resolves the poll:
   - **Bot mention:** the channel's pointer.
   - **Slash command:** the team's only open poll. If there are several, the one in `#lunch_buddies`. Otherwise it replies asking the user to close from the channel.
   - Then it runs `ClosePoll`. "No poll found" and "already closed" come back inline.
   - **[rev 3]** Because close deletes the pointer, closing an already-closed poll from a channel now says "No poll found" rather than "already closed".
2. The router starts `ClosePoll` with execution name `close-<callback_id>`.
3. `form-groups`:
   - If `group_count` is already set, return the existing groups.
   - Otherwise group the "yes" answers, `SaveGroups`, and DM the closer "No poll responses found" if nobody answered at all.
4. Map: `notify-group` (in-channel or private group DM; skip if `notified_at` is set).
   - **[rev 3]** A failed group doesn't stop the others.
   - After the Map, `MarkPollComplete` runs. If any group failed, the execution then ends in `Fail`, which triggers the alarm.

### 5.4 Other endpoints

| Endpoint | Notes |
|----------|-------|
| `/auth` | Exchanges the code, upserts the team, sends the welcome DM. Logs only team id/name (P9). **[rev 4]** No longer looks up the installer or creates/updates a Stripe customer, and the welcome DM no longer links to pricing. |
| `summary` | **[rev 3]** Skips polls with no groups instead of erroring (Python raised `groups not found`). |
| Invoicing | **[rev 4] Removed** along with Stripe. The Python job always ran with `dry_run=True`, so it never billed anyone. The legacy `stripe_customer_id`, `invoicing_enabled` and `stripe_invoice_id` columns are not migrated. |
| `/error` | Dropped. |
| `scripts/*` | **[rev 3]** Dropped, not ported. `close_all_polls_for_team.py` was a one-off with the team name hard-coded. `generate_app_store_content.py` only printed `AppExplanation` (now `polls.AppExplanation`). `save_to_sql.py` and `analysis.py` were ad-hoc analysis of the old tables; they're in git history if needed. |

### 5.5 Behaviour quirks kept for parity [rev 3]

- **Group size.** The minimum group size is `group_size - 1`, so small polls can produce a group of 1. For example, 3 "yes" answers at `size=2` give groups of 2 and 1. This is Python's `_get_groups`, ported exactly. Its test cases are the parity spec, compared by group sizes because the RNG differs.
- **Channel lookup.** `conversations.list` lists public channels only, as the Python client did; private channels would need the `groups:read` scope.
- **`as_user`.** Messages are still sent with `as_user: true`.

## 6. Idempotency and failure handling

| Layer | Mechanism |
|-------|-----------|
| HTTP create | `attribute_not_exists` on a fresh UUID. Retried bot events ignored. |
| Stream → router | Batch size 10. 5 retries. Bisect on error. `ReportBatchItemFailures`. On-failure SQS DLQ (`<stack>-stream-dlq`), with an alarm. |
| Router → SFN | Deterministic execution names. `ExecutionAlreadyExists` counts as success. |
| prepare-poll | Conditional transitions. Re-runs skip to listing members. |
| poll-user / notify-group | `sent_at` / `notified_at` markers. A crash between the Slack post and the marker can still double-send once. |
| form-groups | `group_count` + groups in one transaction (§4.3). |
| Slack rate limits | `slack.RateLimitedError` is returned **unwrapped**, so aws-lambda-go reports `errorType: RateLimitedError` and the SFN `Retry` matches it (backoff from 3s, up to 8 attempts, jitter). Wrapping it with `fmt.Errorf` would break the match. |
| Alarms | An SNS topic `<stack>-alarms`, fed by an EventBridge rule on SFN `FAILED`/`TIMED_OUT`/`ABORTED` and by the DLQ depth alarm. `EnvConfig.AlertEmail` (empty for now) adds an email subscription. |

## 7. Code structure (as built)

```
Makefile                         # make build → dist/<lambda>.zip for each cmd; test; vet; fmt-check
cmd/{apigateway,dynamostream,worker}/main.go   # the three Lambdas
cmd/migrate/main.go                            # local CLI
internal/
  polls/          parse.go grouping.go messages.go       # pure domain + parity tests
  repositories/   main.go teams.go polls.go               # single table; recording-fake tests
  repositories/memory/                                    # in-memory impl with the same conditions, for service tests
  server/         main.go polls.go respond.go bot.go auth.go service_context.go
  workflows/      deps.go router.go worker.go start_poll.go close_poll.go
  slack/ (+ slacktest/)  slackverify/  migrate/
cdk/              main.go stack.go data.go lambdas.go apigateway.go domain.go workflows.go stream.go alarms.go iam.go
cdk/statemachines/start_poll.asl.json close_poll.asl.json
.github/workflows/ci.yml pr.yml deploy.yml               # Python main.yml removed
```

**Testing:**
- `go test -race ./...` covers the domain parity cases, repository request shapes and error mapping, and every HTTP route against the in-memory store.
- It also covers a full create → DM → respond → close → group → notify lifecycle, idempotent re-runs of every task, the stream classifier (including the guarantee that migrated rows don't trigger anything), and the migration transforms.
- `cdk synth --all` runs in CI.
- The ASL is checked as JSON in CI but has **not** been validated against AWS yet. Run `aws stepfunctions validate-state-machine-definition` (or a dev deploy) before relying on it.

## 8. Migration and cutover

### 8.1 Prerequisites per stack

- **SSM Parameter Store parameters** at `/lunch-buddies/<env>/<key>`: `slack_signing_secret`, `slack_verification_token`, `slack_client_id`, `slack_client_secret`, `auth_url` (the README has a command to set them), plus the optional `legacy_forward_url` (§8.3).
  - **[rev 4]** These replace rev 3's Secrets Manager secret because they're free.
  - The API Lambda reads them at cold start (`internal/params`, `ssm:GetParametersByPath` on its own prefix only) rather than having CloudFormation copy them into env vars. The deploy-time approach only picked up a changed value on a deploy that also changed the function, and a stale `auth_url` broke the first dev install.
  - Values now take effect on the next cold start, never sit in the Lambda's configuration, and can be SecureString (AWS-managed `aws/ssm` key).
  - A missing required parameter makes the API fail to start, which the deploy's ping check catches. SSM can't store an empty value, and the verification token must never be a placeholder, because the code would accept it as valid.
- **The OIDC deploy role** `github-actions-deploy` must trust this repository for both the `dev` and `prod` GitHub environments. Dev deploys from PRs already work.

### 8.2 Why removing the Python in this PR is safe [rev 3]

- The Zappa deployment (Lambda, API Gateway, SQS queues, tables) lives in AWS, not in the repo, so it keeps serving Slack until cutover.
- `main.yml` could no longer deploy anyway: GitHub's runners no longer provide Python 3.8.
- `zappa_settings.json` is in git history (`git show 2aa093f:zappa_settings.json`) for the final `zappa undeploy`.

### 8.3 Forwarding mode [rev 4]

Changing the prod Slack app's URLs needs Slack's review, so **traffic moves to the new API whenever Slack approves, not when we choose**. To keep that from also being the data cutover, the API has a temporary forwarding mode (`internal/server/forward.go`):
- **When it's on:** while `/lunch-buddies/<env>/legacy_forward_url` is set (prod: `https://ahlfhssbq3.execute-api.us-west-2.amazonaws.com/production`).
- **What it does:** every Slack route is passed through to the Zappa API (`/v1/poll/create` → `/api/v0/poll/create`, and so on), with the body, Slack headers and query string unchanged. Status, body, `Content-Type` and `Location` (the `/install` and `/auth` redirects, unfollowed) come back to Slack. The Python app authenticates with the verification token in the body, so the body has to be untouched.
- **What stays local:** `/v1/ping`, so deploy health checks keep working.
- **What it doesn't touch:** the new table. Nothing is written there, so no workflows start.

Turning it off is the cutover. Turning it back on is the rollback, with no Slack review needed.

### 8.4 Migration tool

`go run ./cmd/migrate -target lunch-buddies-<env>-records` defaults to `-dry-run=true` and prints counts. Pass `-dry-run=false` to write. The legacy table names default to `lunch_buddies_*`. **[rev 4]** Dev and prod Zappa shared those tables (`dynamo-dao` adds no stage prefix), so **migrate into prod only**. Dev starts empty, so real workspaces' bot tokens never end up in dev.

Mapping:
- **Teams** are copied as they are. A team already in the new table is left alone.
- **Polls:** `CREATED` → `OPEN`. `CLOSED` → `COMPLETE` with `group_count`, because the old system already notified those groups.
- **[rev 4] Polls closed since they were copied:** if a poll was copied while open and has since closed in Zappa, `migrate.CompleteIfOpen` moves the copy `OPEN` → `COMPLETE` and releases its pointer. Without this, closing it again in the new system would notify its groups twice. Both writes are conditional, so a poll the new system already moved on, or a pointer that now belongs to a newer poll, is left alone. `OPEN` → `COMPLETE` doesn't match the stream filter.
- **Pointers:** an `ACTIVE_POLL` pointer for the newest open poll in each channel, whatever its age, so old open polls stay closable.
- **Groups** get key `GROUP#<key>#m<hash of members>`, stable across re-runs, and are marked notified.
- **Every other write** is `attribute_not_exists(pk)`, so re-runs never clobber newer data. Nothing is inserted as `REQUESTED`, so no workflows fire.

### 8.5 Production rollout [rev 4]

1. **Before merging:**
   1. Create the five prod parameters with the **prod** Slack app's values, plus `legacy_forward_url`.
   2. Confirm the deploy role trusts the `prod` environment.
   3. The first prod deploy creates `lunch-buddies-prod`. CI's "Refuse to deploy over a stack this app didn't create" step fails the deploy if a stack with that name already exists without this app's outputs. That's the guard against a repeat of the dev collision (§8.6).
2. **Merge.** `deploy.yml` deploys prod on every push to `master`. Because of `legacy_forward_url`, prod's API is in forwarding mode, and Slack still calls Zappa directly, so nothing user-visible changes. The ping check confirms the domain, the certificate and that all parameters loaded. The API's log shows `FORWARDING MODE` on each cold start.
3. **Submit the prod Slack app changes:** the same `/v1` URL table as dev, on `api.lunchbuddiesapp.com`. Keep the old Redirect URL listed too, because installs still complete through Zappa's OAuth flow until cutover.
4. **When Slack approves,** traffic flows Slack → new API → Zappa. Confirm with `forwarded to legacy API` lines in `/aws/lambda/lunch-buddies-prod-api`. The website's "Add to Slack" button can now point at `https://api.lunchbuddiesapp.com/v1/install`.
5. **Cut over on a quiet evening** (check for open polls first; the README has a scan for `CREATED` polls):
   1. Run `migrate` with `-dry-run`, check the counts, then run it with `-dry-run=false`.
   2. Delete `/lunch-buddies/prod/legacy_forward_url` and recycle the API Lambda (`aws lambda update-function-configuration ... --description ...`, see the README).
   3. Re-run `migrate` to pick up anything Zappa wrote in the seconds between, including any `CREATED` → `CLOSED`.
   4. Watch one real create → respond → close cycle in the logs and Step Functions.
6. **Rollback:** put `legacy_forward_url` back and recycle the Lambda. Anything created in the new system after cutover won't exist in Zappa's tables, so roll back early or not at all.

### 8.6 Decommission (about 2 weeks after cutover)

- Remove forwarding mode (`forward.go`, the `legacy_forward_url` key) and the old Redirect URL from the Slack app.
- **Prod:** `zappa undeploy production` (restore `zappa_settings.json` from history first), then delete the `polls_to_start` / `users_to_poll` / `polls_to_close` / `groups_to_notify` / `error` queues.
- **Dev: do NOT run `zappa undeploy dev` or `zappa update dev`.** **[rev 4]** Zappa names its CloudFormation stack `<project>-<stage>`, so its dev stack was also called `lunch-buddies-dev`. The first CDK dev deploy updated that 2018 stack in place: it deleted Zappa's dev REST API (4 resources) and added ours, and Zappa would now act on our stack. Delete the old dev Lambda (`lunch-buddies-dev`), its SQS event source mappings and the `dev_*` queues by hand. Prod doesn't collide (Zappa's is `lunch-buddies-production`), and CI now refuses to deploy over a stack it didn't create.
- Export, then delete the old `lunch_buddies_*` tables.
- **Delete the old Zappa log groups (P9): they contain bot tokens.**

## 9. Implementation status

| # | Step | Status |
|---|------|--------|
| 1 | Scaffold (go.mod, Makefile, CI, CDK skeleton) | Done |
| 2 | Domain port + parity tests | Done |
| 3 | Repositories + in-memory store | Done |
| 4 | Slack client, request verification | Done |
| 5 | Workflow tasks, router, ASL, stream mapping, DLQ, alarms | Done (ASL not yet validated against AWS) |
| 6 | HTTP endpoints | Done |
| 7 | Invoice | **Removed [rev 4]** |
| – | Consolidate task Lambdas into `cmd/worker` | Done **[rev 4]** |
| 8 | Migration tool | Done (not run against real data) |
| – | Remove Python, Zappa config and `main.yml`; Go README | Done **[rev 3]** |
| 9 | SSM parameters, dev deploy | **Done [rev 4]**: dev stack deployed from PR CI; ping OK on `dev-api.lunchbuddiesapp.com` |
| 9b | Point dev Slack app at the dev domain, install | Done |
| 10 | Forwarding mode, `CompleteIfOpen`, prod deploy on merge with stack-ownership guard | Done **[rev 4]** |
| 11 | Production rollout (§8.5) | **Next** |
| 10 | Prod cutover, then decommission | After 9 |

## 10. Alternatives considered

- **Keep Python, only move to single table + SFN** (rev 1). Superseded.
- **A fresh repo from go-template.** We rewrote in place instead to keep history; the Python is removed in the same PR.
- **EventBridge Pipes instead of the router Lambda.** It can't set deterministic execution names.
- **Synchronous channel resolution in the API.** The slash-command path needs Slack pagination inside the 3s budget.
- **Step Functions HTTP Task calling Slack.** Bot tokens are per-team.
- **[rev 3] Recipient rows written in bulk by prepare-poll.** Rejected because BatchWrite can't be conditional (§5.1).

## 11. Open questions

1. ~~**Custom domains.**~~ **Resolved [rev 4]:** `api.lunchbuddiesapp.com` (prod) and `dev-api.lunchbuddiesapp.com` (dev), in the `lunchbuddiesapp.com` hosted zone (`Z06652991WJMIVK3Y60MY`) in this account.
2. **Old table names.** The Python DAOs hard-code `lunch_buddies_*` with no stage prefix. Do dev and prod Zappa share the same tables, or does `dynamo_dao` add a prefix? This decides which tables `migrate` reads for each env; they're configurable with `-teams-table` etc.
3. **The dev Slack app.** Does the one behind `VERIFICATION_TOKEN_DEV` still exist?
4. **OIDC role trust.** Does `github-actions-deploy` trust `qsweber/lunch-buddies`?
5. **Alert email.** Where should `EnvConfig.AlertEmail` send alerts?
6. **Other readers.** Does `lunch-buddies-web`, or anything else, read the old `lunch_buddies_*` tables? (The Python analysis scripts were dropped; see §5.4.)
7. **Group size.** Keep the parity quirk that allows groups of 1 (§5.5)?

## 12. Deferred: encrypting bot tokens

Bot tokens remain plaintext in DynamoDB, as today, by decision on this PR. Anyone who can read the table, its exports or backups, or the stream can use them. If we revisit this:

- **Approach.** Encrypt the token in the application with a dedicated KMS key, using `team_id` as encryption context. Do it in `TeamsRepository.PutTeam`/`GetTeam`, cache decrypted tokens per Lambda instance, and grant `kms:Decrypt` only to the API and worker roles.
- **Cost.** About $1/month per key. At this volume, requests stay within the 20k/month free tier.
- **Migration.** Encrypt in `cmd/migrate`, plus a one-off re-encrypt of existing rows.
- **Optional.** Slack token rotation, so leaked tokens expire after 12 hours.

The rest of P9 (no token logging, log retention, deleting the old log groups) is independent of this and already done or planned.
