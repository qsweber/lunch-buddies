# Lunch Buddies Go Rewrite Requirements

## 1. Purpose

Reimplement the current Python backend in Go while preserving externally observable behavior for Slack users, AWS-triggered workflows, and persisted data semantics.

## 2. Product Scope

The service coordinates “lunch buddy” grouping in Slack workspaces:

- Installs into a Slack workspace via OAuth.
- Creates lunch polls (sync command -> async fanout).
- Collects individual responses.
- Closes polls and builds groups by selected lunch time.
- Notifies groups (channel thread or private group DM mode).
- Supports summary retrieval and monthly invoicing logic.

## 3. Runtime Architecture

### 3.1 Components

1. **HTTP app** (Slack-facing request/response endpoints).
2. **Async queue workers** (SQS-triggered handlers).
3. **Persistence layer** (DynamoDB tables via DAO abstraction).
4. **External integrations**:
   - Slack Web API
   - Stripe
   - SQS
   - Slack OAuth HTTP call

### 3.2 Processing model

- Slack HTTP requests must return quickly (under Slack timeout expectations), so expensive work is queued.
- Queue pipeline:
  - `polls_to_start` -> `users_to_poll` -> direct Slack poll messages
  - `polls_to_close` -> `groups_to_notify` -> group notifications

## 4. External Interfaces

## 4.1 HTTP Routes

Implement these routes and semantics:

- `POST /api/v0/poll/create`
  - Validates Slack verification token and team authorization.
  - Enqueues poll creation request.
  - Responds with JSON `{ "text": "<status/help/error>" }`.

- `POST /api/v0/poll`
  - Handles Slack interactive poll button response payload.
  - Stores a poll response keyed by `(callback_id, user_id)`.
  - Returns modified original Slack message payload with confirmation attachment.

- `POST /api/v0/poll/close`
  - Validates token/team.
  - Enqueues poll closure request.
  - Responds with JSON `{ "text": "<status/help>" }`.

- `POST /api/v0/help`
  - Validates token/team.
  - Returns app help text.

- `GET /api/v0/install`
  - Redirects to OAuth authorization URL from environment.

- `GET /api/v0/auth`
  - Exchanges OAuth code with Slack.
  - Upserts team, syncs Stripe customer, DMs installer.
  - Redirects to registration URL.

- `POST /api/v0/bot`
  - Validates token/team.
  - Parses Slack event callback payload (including edited message shape).
  - Supports commands: `create`, `close`, `summary`, `help`.
  - Returns `"ok", 200`.

- `GET /api/v0/error` (diagnostic route)
  - Enqueues test message and raises error.

All JSON responses from Slack-interactive endpoints should include `Access-Control-Allow-Origin: *`.

## 4.2 Queue Handlers

Implement SQS event handlers:

- `create_poll_from_queue`:
  - Input: `PollsToStartMessage`
  - Output queue: `users_to_poll`

- `poll_users_from_queue`:
  - Input: `UsersToPollMessage`
  - Side effect: send poll DM to user

- `close_poll_from_queue`:
  - Input: `PollsToCloseMessage`
  - Output queue: `groups_to_notify`

- `notify_groups_from_queue`:
  - Input: `GroupsToNotifyMessage`
  - Side effect: send group notification

Error handling requirement for queue handlers:
- On processing failure, set message visibility timeout with linear backoff (`attempts * 10s`, max 600s), capture exception, and rethrow.

## 5. Domain Model Requirements

## 5.1 Team

Fields:
- `team_id` (PK)
- `access_token` (legacy/deprecated field still persisted)
- `bot_access_token`
- `name`
- `created_at`
- `feature_notify_in_channel` (boolean)
- `invoicing_enabled` (optional boolean)
- `stripe_customer_id` (optional string)

## 5.2 Poll

Fields:
- `team_id` (partition key)
- `created_at` (sort key)
- `channel_id`
- `created_by_user_id`
- `callback_id` (UUID)
- `state` (`CREATED` or `CLOSED`)
- `choices` (list of choices)
- `group_size` (int)
- `stripe_invoice_id` (optional string)

Compatibility requirements:
- Existing persisted poll rows may have missing `channel_id` and legacy `choices` formats; parser must handle historic variants.

## 5.3 PollResponse

Fields:
- `callback_id`
- `user_id`
- `created_at`
- `response` (choice key)

Uniqueness:
- `(callback_id, user_id)` unique (later response overwrites/update behavior through DAO uniqueness semantics).

## 5.4 Group

Fields:
- `callback_id`
- `user_ids` (list serialized as JSON in storage)
- `response_key`

## 6. Business Rules

## 6.1 Authorization and tenancy

- Every Slack request must pass token validation:
  - Allowed if token equals `VERIFICATION_TOKEN` or `VERIFICATION_TOKEN_DEV`.
- Team must exist in Teams store for operational routes.

## 6.2 Poll creation

- If command text is exactly `help` (case/whitespace normalized), return create-help text instead of queueing.
- Custom poll options parsing:
  - Accept comma-separated 24h times in `HHMM`/`HMM` integer form.
  - Always append a `No` option.
- Optional size override syntax: `size=<n>`.
  - Allowed range: 2..6 inclusive.
  - Default group size: 6.
- If no custom text, default choices are `Yes (12:00)` and `No`.
- Channel selection:
  - Slash flow (`channel_id` missing): use default channel `lunch_buddies`.
  - If default channel absent, DM creator with specific error and abort.
  - If creator not in default channel, DM creator with specific error and abort.
- Prevent duplicate active poll:
  - If latest poll in same channel is not closed and created within 24 hours, DM creator “There is already an active poll” and abort.
- On success:
  - Create poll record.
  - Enqueue one `UsersToPollMessage` per member in target channel.

## 6.3 Polling users

- Only send poll DM if referenced poll state is `CREATED`.
- Message text: participation question plus button attachment containing all poll choices.

## 6.4 Recording poll responses

- Resolve selected choice from poll definition.
- Persist response with action timestamp.
- Return original message with appended acknowledgement attachment.

## 6.5 Closing poll

- If close text is `help`, return close-help text and do not queue.
- If no channel passed, attempt default `lunch_buddies` channel.
- Fetch latest poll for team/channel:
  - If none: notify requester “No poll found”.
  - If already closed: notify requester “already been closed”.
  - If no responses: notify requester, mark poll closed, stop.
- Grouping:
  - Ignore `No` responses.
  - Group per selected `Yes` choice.
  - Use randomized grouping with target `group_size`, min `group_size-1` (at least 1), max 7.
  - If final group too small, redistribute or recursively reduce group size.
- Mark poll closed immediately before emitting group notifications.
- Emit one `GroupsToNotifyMessage` per resulting group.

## 6.6 Group notification

- Persist `Group` row before sending notifications.
- If `feature_notify_in_channel = true`:
  - Intersect group users with current channel members (exclude users who left).
  - Post channel message tagging included users and meeting time.
  - Post threaded follow-up assigning one random user to pick location.
- Else:
  - Open multi-person DM with all group users.
  - Post intro message with meeting time and random “in charge” user.

## 6.7 Bot command behavior

- Parse mention text and normalize lowercased, trimmed punctuation.
- Supported first tokens:
  - `create`: queue create poll
  - `close`: queue close poll
  - `summary`: return historical summary
  - `help`: return app explanation text
- Unknown commands are ignored (no reply).

## 6.8 Summary generation

- Default lookback window: 7 days.
- If command suffix contains an integer, use as lookback days.
- Summaries include:
  - Poll date localized to requesting user’s Slack timezone.
  - Poll starter mention.
  - Group lines by choice with user mentions.
- Requires existing groups for summarized polls; missing groups is treated as error.

## 6.9 OAuth installation flow

- Exchange auth code against `https://slack.com/api/oauth.v2.access`.
- Read installer user info via Slack API.
- Team upsert logic:
  - Existing team: update name/token and preserve key feature flags.
  - New team: create with defaults:
    - `feature_notify_in_channel = true`
    - `invoicing_enabled = true`
- Stripe behavior:
  - If no existing Stripe customer, create one from installer user/team info.
  - If customer exists, update it.
- DM installer with onboarding message (pricing line included only when invoicing enabled).

## 6.10 Invoicing

- Periodic invoice job processes teams eligible for billing:
  - Team has `stripe_customer_id`.
  - `invoicing_enabled = true`.
  - Team created before first day of month at least ~1 full month ago (current algorithm: `(first_of_month - 15 days) -> first_of_that_month` cutoff).
- Polls billable if:
  - `state == CLOSED`
  - `stripe_invoice_id` is null
  - created later than `(team.created_at + 30 days)`
- Bill amount = number of unique users with `yes_*` responses across billable polls, multiplied by 1.0 (USD units currently stored as float in line item).
- If amount is zero, skip invoice.
- If not dry-run and invoice created, mark all included polls with new invoice id.

## 7. Storage and Serialization Requirements

- Preserve Dynamo table names:
  - `lunch_buddies_Team`
  - `lunch_buddies_Poll`
  - `lunch_buddies_PollResponse`
  - `lunch_buddies_Group`
- Preserve key structures and lookup behavior used by app logic.
- SQS payload serialization must round-trip:
  - UUID
  - datetime
- Poll choices deserialization must support:
  1. map format (`{key: display_text}`)
  2. list-of-pairs format (`[[key, display_text], ...]`)
  3. canonical list-of-objects format

## 8. Environment and Configuration

Required runtime config includes:

- `VERIFICATION_TOKEN`
- `VERIFICATION_TOKEN_DEV`
- `AUTH_URL`
- `CLIENT_ID`
- `CLIENT_SECRET`
- `STAGE` (`production` vs non-prod for queue naming)
- `STRIPE_API_KEY` (optional; billing no-ops when absent)

Deployment topology currently maps:
- Flask app as Lambda HTTP handler.
- Separate Lambda event handlers bound to SQS queues per stage (`dev_*` and prod names).

## 9. Observability and Error Handling

- Capture exceptions through Sentry integration.
- Log key inputs/events for auth, bot parsing, poll lifecycle, and invoicing.
- For recoverable user issues (missing channel, no poll, already closed), send user-facing Slack messages instead of hard-failing workflows.

## 10. Non-Functional Requirements for Go Rewrite

- Preserve external API contracts and message semantics to avoid Slack app regression.
- Keep request handling fast enough for Slack expectations by retaining async queue fanout.
- Maintain deterministic data compatibility with existing Dynamo records.
- Preserve stage-aware queue routing behavior.
- Preserve idempotency characteristics implicit in current flow (especially queue retries + unique keys).

## 11. Suggested Acceptance Checklist

- HTTP endpoints parity validated with fixture-based request tests.
- Queue message contracts are backward-compatible.
- Existing Dynamo rows (including legacy choice formats) are readable.
- Poll lifecycle end-to-end parity:
  - create -> fanout -> respond -> close -> notify
- OAuth install/update parity and installer DM behavior.
- Summary and invoicing outputs match Python behavior for representative fixtures.

