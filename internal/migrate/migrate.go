// Package migrate supports the production cutover from the legacy Python app. Only teams
// (and their bot tokens) are carried over: old polls, responses and groups are left behind.
// Because of that, the cutover must not happen while a legacy poll is in flight (InFlight),
// or its buttons and close would reach a new system that has never heard of it.
//
// The transforms are pure so they can be unit tested; cmd/migrate does the I/O.
package migrate

import (
	"fmt"
	"math/big"
	"sort"
	"strings"
	"time"

	"github.com/qsweber/lunch-buddies/internal/repositories"
)

// Row is a legacy item with every attribute converted to a plain string (numbers keep their
// decimal text, so timestamps keep full precision); NULL attributes are absent.
type Row map[string]string

// epochMillis converts a legacy Decimal epoch-seconds timestamp to Unix milliseconds.
func epochMillis(r Row, k string) (int64, error) {
	raw := r[k]
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

// Team converts a legacy lunch_buddies_Team row.
func Team(r Row) (repositories.Team, error) {
	if r["team_id"] == "" || r["bot_access_token"] == "" {
		return repositories.Team{}, fmt.Errorf("team %q: missing team_id or bot_access_token", r["team_id"])
	}
	created, err := epochMillis(r, "created_at")
	if err != nil {
		return repositories.Team{}, fmt.Errorf("team %s: %w", r["team_id"], err)
	}
	notify := strings.ToLower(r["feature_notify_in_channel"])
	return repositories.Team{
		TeamID:                 r["team_id"],
		BotAccessToken:         r["bot_access_token"],
		Name:                   r["name"],
		CreatedAt:              created,
		FeatureNotifyInChannel: notify == "1" || notify == "true",
	}, nil
}

// LegacyPoll is the part of a lunch_buddies_Poll row the in-flight check reports.
type LegacyPoll struct {
	TeamID    string
	ChannelID string
	CreatedAt time.Time
}

func (p LegacyPoll) String() string {
	channel := p.ChannelID
	if channel == "" {
		channel = "-"
	}
	return fmt.Sprintf("%s  team=%s  channel=%s", p.CreatedAt.UTC().Format(time.RFC3339), p.TeamID, channel)
}

// InFlight splits the legacy polls still in state CREATED into those created within window
// of now (in flight: people may still answer or close them) and older ones (abandoned; the
// legacy app also stopped treating a poll as active after a day). Both are sorted newest
// first. Closed polls are ignored.
func InFlight(rows []Row, now time.Time, window time.Duration) (inFlight, stale []LegacyPoll, err error) {
	for _, r := range rows {
		if r["state"] != "CREATED" {
			continue
		}
		ms, err := epochMillis(r, "created_at")
		if err != nil {
			return nil, nil, fmt.Errorf("poll %s: %w", r["callback_id"], err)
		}
		p := LegacyPoll{TeamID: r["team_id"], ChannelID: r["channel_id"], CreatedAt: time.UnixMilli(ms)}
		if p.CreatedAt.After(now.Add(-window)) {
			inFlight = append(inFlight, p)
		} else {
			stale = append(stale, p)
		}
	}
	newestFirst := func(ps []LegacyPoll) {
		sort.Slice(ps, func(i, j int) bool { return ps[i].CreatedAt.After(ps[j].CreatedAt) })
	}
	newestFirst(inFlight)
	newestFirst(stale)
	return inFlight, stale, nil
}
