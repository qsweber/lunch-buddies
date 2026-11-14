package migrate

import (
	"strconv"
	"testing"
	"time"
)

func TestTeam(t *testing.T) {
	team, err := Team(Row{"team_id": "T", "bot_access_token": "xoxb", "name": "Acme", "created_at": "1600000000.5"})
	if err != nil || team.TeamID != "T" || team.BotAccessToken != "xoxb" || team.Name != "Acme" || team.CreatedAt != 1600000000500 {
		t.Errorf("team = %+v, %v", team, err)
	}
	if _, err := Team(Row{"team_id": "T", "created_at": "1600000000"}); err == nil {
		t.Error("a team without a bot token should be an error, not a silent copy")
	}
}

func TestInFlight(t *testing.T) {
	now := time.Date(2026, 11, 11, 20, 0, 0, 0, time.UTC)
	ago := func(d time.Duration) string { return strconv.FormatInt(now.Add(-d).Unix(), 10) }

	rows := []Row{
		{"callback_id": "a", "team_id": "T1", "channel_id": "C1", "state": "CREATED", "created_at": ago(2 * time.Hour)},
		{"callback_id": "b", "team_id": "T2", "state": "CREATED", "created_at": ago(30 * time.Minute)},
		{"callback_id": "c", "team_id": "T1", "state": "CLOSED", "created_at": ago(time.Hour)},
		{"callback_id": "d", "team_id": "T3", "state": "CREATED", "created_at": ago(40 * 24 * time.Hour)},
	}
	inFlight, stale, err := InFlight(rows, now, 24*time.Hour)
	if err != nil {
		t.Fatal(err)
	}
	if len(inFlight) != 2 || inFlight[0].TeamID != "T2" || inFlight[1].TeamID != "T1" {
		t.Errorf("inFlight = %v (want T2 then T1, newest first)", inFlight)
	}
	if len(stale) != 1 || stale[0].TeamID != "T3" {
		t.Errorf("stale = %v", stale)
	}
	if got := inFlight[1].String(); got != "2026-11-11T18:00:00Z  team=T1  channel=C1" {
		t.Errorf("String() = %q", got)
	}
	if _, _, err := InFlight([]Row{{"state": "CREATED"}}, now, time.Hour); err == nil {
		t.Error("a CREATED poll without created_at must fail the check, not pass it")
	}
}
