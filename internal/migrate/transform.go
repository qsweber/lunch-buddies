// Package migrate converts rows from the four legacy Python tables (lunch_buddies_Team,
// _Poll, _PollResponse, _Group) into single-table items. The transforms are pure so they can
// be unit tested; cmd/migrate does the scanning and writing.
package migrate

import (
	"crypto/sha1"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/big"
	"sort"
	"strings"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
)

// Row is a legacy item, unmarshalled with attributevalue into plain Go values
// (numbers arrive as strings via json.Number-like handling; see num).
type Row map[string]any

func str(r Row, k string) string {
	v, ok := r[k]
	if !ok || v == nil {
		return ""
	}
	return fmt.Sprint(v)
}

// epochMillis converts the legacy Decimal epoch-seconds timestamps to Unix milliseconds.
func epochMillis(r Row, k string) (int64, error) {
	raw := str(r, k)
	if raw == "" {
		return 0, fmt.Errorf("missing %s", k)
	}
	f, _, err := big.ParseFloat(raw, 10, 128, big.ToNearestEven)
	if err != nil {
		return 0, fmt.Errorf("bad %s %q: %w", k, raw, err)
	}
	ms, _ := new(big.Float).Mul(f, big.NewFloat(1000)).Int64()
	return ms, nil
}

func boolish(r Row, k string) bool {
	switch strings.ToLower(str(r, k)) {
	case "1", "true":
		return true
	}
	return false
}

// Team converts a legacy team. The bot token is still plaintext here; the teams repository
// encrypts it on write.
func Team(r Row) (repositories.Team, error) {
	created, err := epochMillis(r, "created_at")
	if err != nil {
		return repositories.Team{}, err
	}
	return repositories.Team{
		TeamID:                 str(r, "team_id"),
		BotAccessToken:         str(r, "bot_access_token"),
		Name:                   str(r, "name"),
		CreatedAt:              created,
		FeatureNotifyInChannel: boolish(r, "feature_notify_in_channel"),
		StripeCustomerID:       str(r, "stripe_customer_id"),
		InvoicingEnabled:       boolish(r, "invoicing_enabled"),
	}, nil
}

// Poll converts a legacy poll. Legacy CREATED becomes OPEN; legacy CLOSED becomes COMPLETE
// (the old system already notified its groups), with group_count recorded so the new
// FormGroups task would treat it as done.
func Poll(r Row, groupCount int) (repositories.Poll, error) {
	created, err := epochMillis(r, "created_at")
	if err != nil {
		return repositories.Poll{}, err
	}
	choices, err := Choices(str(r, "choices"))
	if err != nil {
		return repositories.Poll{}, fmt.Errorf("poll %s: %w", str(r, "callback_id"), err)
	}
	groupSize := polls.DefaultGroupSize
	if gs := str(r, "group_size"); gs != "" {
		if _, err := fmt.Sscan(gs, &groupSize); err != nil {
			return repositories.Poll{}, fmt.Errorf("bad group_size %q", gs)
		}
	}

	p := repositories.Poll{
		CallbackID:      str(r, "callback_id"),
		TeamID:          str(r, "team_id"),
		ChannelID:       str(r, "channel_id"),
		CreatedByUserID: str(r, "created_by_user_id"),
		CreatedAt:       created,
		Choices:         choices,
		GroupSize:       groupSize,
		StripeInvoiceID: str(r, "stripe_invoice_id"),
	}
	switch state := str(r, "state"); state {
	case "CREATED":
		p.State = repositories.StateOpen
	case "CLOSED":
		p.State = repositories.StateComplete
		p.GroupCount = &groupCount
	default:
		return repositories.Poll{}, fmt.Errorf("poll %s: unknown state %q", p.CallbackID, state)
	}
	return p, nil
}

// Choices parses the three historical encodings of the choices column:
// v1 {"yes_1200": "Yes (12:00)", ...}, v2 [["yes_1200", "Yes (12:00)"], ...], and the
// current [{"key": ..., "is_yes": ..., "time": ..., "display_text": ...}, ...].
func Choices(raw string) ([]polls.Choice, error) {
	legacy := func(key, display string) polls.Choice {
		isYes := strings.Contains(key, "yes")
		t := ""
		if isYes && len(key) >= 4 {
			t = key[len(key)-4:len(key)-2] + ":" + key[len(key)-2:]
		}
		return polls.Choice{Key: key, IsYes: isYes, Time: t, DisplayText: display}
	}

	var v1 map[string]string
	if err := json.Unmarshal([]byte(raw), &v1); err == nil {
		keys := make([]string, 0, len(v1))
		for k := range v1 {
			keys = append(keys, k)
		}
		// JSON object order is lost; keep yes options first (sorted by time), "no" last.
		sort.Slice(keys, func(i, j int) bool {
			if (keys[i] == "no") != (keys[j] == "no") {
				return keys[j] == "no"
			}
			return keys[i] < keys[j]
		})
		out := make([]polls.Choice, len(keys))
		for i, k := range keys {
			out[i] = legacy(k, v1[k])
		}
		return out, nil
	}

	var v2 [][]string
	if err := json.Unmarshal([]byte(raw), &v2); err == nil && len(v2) > 0 && len(v2[0]) == 2 {
		out := make([]polls.Choice, len(v2))
		for i, pair := range v2 {
			out[i] = legacy(pair[0], pair[1])
		}
		return out, nil
	}

	var v3 []polls.Choice
	if err := json.Unmarshal([]byte(raw), &v3); err != nil {
		return nil, fmt.Errorf("unrecognised choices %q: %w", raw, err)
	}
	return v3, nil
}

// Response converts a legacy poll response.
func Response(r Row) (repositories.PollResponse, error) {
	created, err := epochMillis(r, "created_at")
	if err != nil {
		return repositories.PollResponse{}, err
	}
	return repositories.PollResponse{
		CallbackID: str(r, "callback_id"),
		UserID:     str(r, "user_id"),
		Response:   str(r, "response"),
		CreatedAt:  created,
	}.WithKeys(), nil
}

// Group converts a legacy group. Legacy groups have no ordinal, so the sort key uses a hash
// of the members: stable across re-runs of the migration, and distinct from the
// "#000"-style keys new groups get.
func Group(r Row) (repositories.Group, error) {
	var userIDs []string
	if err := json.Unmarshal([]byte(str(r, "user_ids")), &userIDs); err != nil {
		return repositories.Group{}, fmt.Errorf("bad user_ids: %w", err)
	}
	sorted := append([]string(nil), userIDs...)
	sort.Strings(sorted)
	sum := sha1.Sum([]byte(strings.Join(sorted, ",")))

	callbackID := str(r, "callback_id")
	responseKey := str(r, "response_key")
	return repositories.Group{
		PK:          repositories.PollPartitionKey(callbackID),
		SK:          fmt.Sprintf("GROUP#%s#m%s", responseKey, hex.EncodeToString(sum[:4])),
		CallbackID:  callbackID,
		ResponseKey: responseKey,
		UserIDs:     userIDs,
		NotifiedAt:  1, // the legacy system already notified it
	}, nil
}

// ActivePointers returns an ACTIVE_POLL pointer for the newest OPEN poll in each channel,
// so polls that are open at cutover can still be closed. Polls without a channel (very old
// rows) are skipped.
func ActivePointers(pollsList []repositories.Poll) []repositories.ActivePoll {
	latest := map[string]repositories.Poll{}
	for _, p := range pollsList {
		if p.State != repositories.StateOpen || p.ChannelID == "" {
			continue
		}
		k := p.TeamID + "|" + p.ChannelID
		if cur, ok := latest[k]; !ok || p.CreatedAt > cur.CreatedAt {
			latest[k] = p
		}
	}
	keys := make([]string, 0, len(latest))
	for k := range latest {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	out := make([]repositories.ActivePoll, 0, len(keys))
	for _, k := range keys {
		p := latest[k]
		out = append(out, repositories.ActivePoll{TeamID: p.TeamID, ChannelID: p.ChannelID, CallbackID: p.CallbackID, CreatedAt: p.CreatedAt}.WithKeys())
	}
	return out
}
