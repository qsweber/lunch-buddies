package server

import (
	"context"
	"encoding/json"
	"net/url"
	"strings"
	"testing"
	"time"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/repositories/memory"
	"github.com/qsweber/lunch-buddies/internal/slack"
	"github.com/qsweber/lunch-buddies/internal/slack/slacktest"
	"github.com/qsweber/lunch-buddies/internal/slackverify"
)

const token = "legacy-token"

var now = time.Date(2026, 11, 3, 18, 0, 0, 0, time.UTC)

type harness struct {
	srv   Server
	store *memory.Store
	slack *slacktest.Fake
	ids   int
}

func newHarness(t *testing.T) *harness {
	t.Helper()
	h := &harness{store: memory.New(), slack: slacktest.New()}
	_ = h.store.PutTeam(context.Background(), repositories.Team{TeamID: "T1", BotAccessToken: "xoxb-1", Name: "Acme"})
	h.srv = New(ServiceContext{
		Repositories: h.store.Repositories(),
		Slack:        h.slack,
		Verifier:     slackverify.Verifier{LegacyTokens: []string{token}},
		Config:       Config{APIBaseURL: "https://api.example.com", ClientID: "123.456", RegistrationURL: "https://example.com/registered"},
		Now:          func() time.Time { return now },
		NewID: func() string {
			h.ids++
			return "cb" + string(rune('0'+h.ids))
		},
	})
	return h
}

func (h *harness) post(path string, form url.Values) Response {
	return h.srv.Handle(context.Background(), Request{Method: "POST", Path: path, Headers: map[string]string{}, Body: form.Encode()})
}

func replyText(t *testing.T, resp Response) string {
	t.Helper()
	if resp.StatusCode != 200 {
		t.Fatalf("status = %d body = %s", resp.StatusCode, resp.Body)
	}
	var body map[string]string
	if err := json.Unmarshal([]byte(resp.Body), &body); err != nil {
		t.Fatal(err)
	}
	return body["text"]
}

func slash(text string) url.Values {
	return url.Values{"token": {token}, "team_id": {"T1"}, "user_id": {"U1"}, "text": {text}}
}

func TestCreatePollWritesRequestedPollOnly(t *testing.T) {
	h := newHarness(t)
	if got := replyText(t, h.post(PathCreatePoll, slash("1145, 1230 size=4"))); got != polls.MsgOK {
		t.Fatalf("reply = %q", got)
	}
	p := h.store.Polls["cb1"]
	if p.State != repositories.StateRequested || p.ChannelID != "" || p.GroupSize != 4 || len(p.Choices) != 3 {
		t.Errorf("poll = %+v", p)
	}
	if len(h.slack.Posted) != 0 {
		t.Error("the API must not call Slack when creating a poll")
	}
}

func TestCreatePollValidationAndHelpAreInline(t *testing.T) {
	h := newHarness(t)
	if got := replyText(t, h.post(PathCreatePoll, slash("noon"))); !strings.HasPrefix(got, "Failed: Option could not be parsed") {
		t.Errorf("reply = %q", got)
	}
	if got := replyText(t, h.post(PathCreatePoll, slash(" HELP "))); got != polls.CreatePollHelp {
		t.Errorf("help reply = %q", got)
	}
	if len(h.store.Polls) != 0 {
		t.Error("no poll should be written")
	}
}

func TestRejectsBadTokenAndUnknownTeam(t *testing.T) {
	h := newHarness(t)
	form := slash("")
	form.Set("token", "wrong")
	if r := h.post(PathCreatePoll, form); r.StatusCode != 401 {
		t.Errorf("bad token status = %d", r.StatusCode)
	}
	form = slash("")
	form.Set("team_id", "T999")
	if r := h.post(PathCreatePoll, form); r.StatusCode != 403 {
		t.Errorf("unknown team status = %d", r.StatusCode)
	}
}

func openPoll(t *testing.T, h *harness, id, channel string) {
	t.Helper()
	ctx := context.Background()
	if err := h.store.CreateRequestedPoll(ctx, repositories.Poll{CallbackID: id, TeamID: "T1", CreatedAt: repositories.At(now), Choices: polls.DefaultChoices(), GroupSize: 6}); err != nil {
		t.Fatal(err)
	}
	if err := h.store.OpenPoll(ctx, h.store.Polls[id], channel, now); err != nil {
		t.Fatal(err)
	}
}

func clickPayload(callbackID, user, value string) url.Values {
	payload, _ := json.Marshal(map[string]any{
		"token":            token,
		"callback_id":      callbackID,
		"action_ts":        "1762192800.123",
		"team":             map[string]string{"id": "T1"},
		"user":             map[string]string{"id": user},
		"actions":          []map[string]string{{"value": value}},
		"original_message": map[string]any{"text": "Are you able", "attachments": []any{map[string]any{"callback_id": callbackID}}},
	})
	return url.Values{"payload": {string(payload)}}
}

func TestRespondRecordsAnswerOnlyWhileOpen(t *testing.T) {
	h := newHarness(t)
	openPoll(t, h, "cbA", "C1")

	resp := h.post(PathRespond, clickPayload("cbA", "U2", "yes_1200"))
	if resp.StatusCode != 200 || !strings.Contains(resp.Body, "Your answer of `Yes (12:00)` was received!") {
		t.Fatalf("resp = %d %s", resp.StatusCode, resp.Body)
	}
	if h.store.Responses["cbA"]["U2"].Response != "yes_1200" {
		t.Error("response not recorded")
	}

	active, _ := h.store.GetActivePoll(context.Background(), "T1", "C1")
	_ = h.store.ClosePoll(context.Background(), *active, "U1", now)
	resp = h.post(PathRespond, clickPayload("cbA", "U3", "yes_1200"))
	if !strings.Contains(resp.Body, "already closed") {
		t.Errorf("late click body = %s", resp.Body)
	}
	if _, ok := h.store.Responses["cbA"]["U3"]; ok {
		t.Error("late response must not be recorded (P3)")
	}
}

func TestCloseSlashCommand(t *testing.T) {
	h := newHarness(t)
	if got := replyText(t, h.post(PathClosePoll, slash(""))); got != polls.MsgNoPollFound {
		t.Errorf("no poll reply = %q", got)
	}

	openPoll(t, h, "cbA", "C1")
	if got := replyText(t, h.post(PathClosePoll, slash(""))); got != polls.MsgOK {
		t.Errorf("close reply = %q", got)
	}
	if p := h.store.Polls["cbA"]; p.State != repositories.StateClosed || p.ClosedByUserID != "U1" {
		t.Errorf("poll = %+v", p)
	}
	if len(h.store.Active) != 0 {
		t.Error("pointer should be released")
	}
}

func TestCloseSlashCommandWithSeveralOpenPollsUsesDefaultChannel(t *testing.T) {
	h := newHarness(t)
	openPoll(t, h, "cbA", "C1")
	openPoll(t, h, "cbB", "C2")
	if got := replyText(t, h.post(PathClosePoll, slash(""))); got != polls.MsgMultipleActivePolls {
		t.Errorf("reply = %q", got)
	}
	h.slack.Channels[polls.DefaultChannelName] = slack.Channel{ID: "C2", Name: polls.DefaultChannelName}
	if got := replyText(t, h.post(PathClosePoll, slash(""))); got != polls.MsgOK {
		t.Errorf("reply = %q", got)
	}
	if h.store.Polls["cbB"].State != repositories.StateClosed || h.store.Polls["cbA"].State != repositories.StateOpen {
		t.Error("should close the #lunch_buddies poll only")
	}
}

func botEvent(text, channel string) string {
	b, _ := json.Marshal(map[string]any{
		"token":   token,
		"type":    "event_callback",
		"team_id": "T1",
		"event":   map[string]any{"type": "app_mention", "channel": channel, "user": "U1", "text": text},
	})
	return string(b)
}

func TestBotCreateAndCloseInChannel(t *testing.T) {
	h := newHarness(t)
	call := func(text string, headers map[string]string) Response {
		if headers == nil {
			headers = map[string]string{}
		}
		headers["content-type"] = "application/json"
		return h.srv.Handle(context.Background(), Request{Method: "POST", Path: PathBot, Headers: headers, Body: botEvent(text, "C9")})
	}

	if r := call("<@UBOT> create 1200.", nil); r.StatusCode != 200 {
		t.Fatalf("status = %d %s", r.StatusCode, r.Body)
	}
	p := h.store.Polls["cb1"]
	if p.ChannelID != "C9" || p.State != repositories.StateRequested {
		t.Errorf("poll = %+v", p)
	}
	if got := h.slack.PostedTo("C9"); len(got) != 1 || got[0] != polls.MsgOK {
		t.Errorf("posted = %v", got)
	}

	// A Slack retry of the same event must not create a second poll.
	call("<@UBOT> create", map[string]string{"x-slack-retry-num": "1"})
	if len(h.store.Polls) != 1 {
		t.Errorf("retry created a poll: %d polls", len(h.store.Polls))
	}

	if err := h.store.OpenPoll(context.Background(), p, "C9", now); err != nil {
		t.Fatal(err)
	}
	call("<@UBOT> close", nil)
	if h.store.Polls["cb1"].State != repositories.StateClosed {
		t.Error("bot close should close the channel's poll")
	}
	call("<@UBOT> close", nil)
	if got := h.slack.PostedTo("C9"); got[len(got)-1] != polls.MsgNoPollFound {
		t.Errorf("second close reply = %q", got[len(got)-1])
	}
}

func TestUninstallAndReinstall(t *testing.T) {
	ctx := context.Background()
	for _, event := range []map[string]any{
		{"type": "app_uninstalled"},
		{"type": "tokens_revoked", "tokens": map[string]any{"bot": []string{"UBOT"}}},
	} {
		h := newHarness(t)
		body, _ := json.Marshal(map[string]any{"token": token, "type": "event_callback", "team_id": "T1", "event": event})
		r := h.srv.Handle(ctx, Request{Method: "POST", Path: PathBot, Headers: map[string]string{}, Body: string(body)})
		if r.StatusCode != 200 {
			t.Fatalf("%v: status %d %s", event["type"], r.StatusCode, r.Body)
		}
		team := h.store.Teams["T1"]
		if team.Installed() || team.BotAccessToken != "" || team.UninstalledAt == nil || !team.UninstalledAt.Equal(now) {
			t.Errorf("%v: team = %+v", event["type"], team)
		}

		// Commands from an uninstalled team are refused.
		if r := h.post(PathCreatePoll, slash("")); r.StatusCode != 403 {
			t.Errorf("%v: create after uninstall = %d", event["type"], r.StatusCode)
		}

		// Reinstalling restores the team and clears the uninstall, keeping the original created_at.
		created := team.CreatedAt
		h.slack.OAuth = &slack.OAuthAccess{AccessToken: "xoxb-again", TeamID: "T1", TeamName: "Acme", UserID: "U1"}
		h.srv.Handle(ctx, Request{Method: "GET", Path: PathAuth, QueryParams: map[string]string{"code": "c"}})
		team = h.store.Teams["T1"]
		if !team.Installed() || team.UninstalledAt != nil || team.CreatedAt != created {
			t.Errorf("%v: after reinstall team = %+v", event["type"], team)
		}
	}
}

func TestUserTokenRevocationIsIgnored(t *testing.T) {
	h := newHarness(t)
	body, _ := json.Marshal(map[string]any{"token": token, "type": "event_callback", "team_id": "T1",
		"event": map[string]any{"type": "tokens_revoked", "tokens": map[string]any{"oauth": []string{"U5"}}}})
	h.srv.Handle(context.Background(), Request{Method: "POST", Path: PathBot, Headers: map[string]string{}, Body: string(body)})
	if !h.store.Teams["T1"].Installed() {
		t.Error("revoking only user tokens must not uninstall the team")
	}
}

func TestBotURLVerification(t *testing.T) {
	h := newHarness(t)
	body := `{"token":"` + token + `","type":"url_verification","challenge":"abc"}`
	r := h.srv.Handle(context.Background(), Request{Method: "POST", Path: PathBot, Headers: map[string]string{}, Body: body})
	if r.StatusCode != 200 || !strings.Contains(r.Body, `"challenge":"abc"`) {
		t.Errorf("resp = %d %s", r.StatusCode, r.Body)
	}
}

func TestParseCommand(t *testing.T) {
	cases := []struct {
		text, typ, first, rest string
		ok                     bool
	}{
		{"<@UBOT> create 1145, 1230", "app_mention", "create", "1145, 1230", true},
		{"<@UBOT> Close.", "app_mention", "close", "", true},
		{"hello there", "app_mention", "", "", false},
		{"summary 14", "message", "summary", "14", true},
	}
	for _, c := range cases {
		first, rest, ok := parseCommand(botMention{Text: c.text, MessageType: c.typ})
		if first != c.first || rest != c.rest || ok != c.ok {
			t.Errorf("parseCommand(%q) = %q %q %v", c.text, first, rest, ok)
		}
	}
}

func TestSummary(t *testing.T) {
	h := newHarness(t)
	openPoll(t, h, "cbA", "C1")
	active, _ := h.store.GetActivePoll(context.Background(), "T1", "C1")
	_ = h.store.ClosePoll(context.Background(), *active, "U1", now)
	_, _ = h.store.SaveGroups(context.Background(), "cbA", []polls.Group{{ResponseKey: "yes_1200", UserIDs: []string{"U2", "U3"}}})
	h.store.Polls["cbA"] = func() repositories.Poll { p := h.store.Polls["cbA"]; p.CreatedByUserID = "U1"; return p }()
	h.slack.Users["U1"] = slack.User{TZ: "America/Los_Angeles"}

	team, _ := h.store.GetTeam(context.Background(), "T1")
	got, err := h.srv.(*ServerImpl).summary(context.Background(), team, "U1", "7 days")
	if err != nil {
		t.Fatal(err)
	}
	want := "*November 03, 2026: started by* <@U1>\nYes (12:00): <@U2> <@U3>"
	if got != want {
		t.Errorf("summary = %q, want %q", got, want)
	}
}

func TestAuthInstallsTeamAndRedirects(t *testing.T) {
	h := newHarness(t)
	h.slack.OAuth = &slack.OAuthAccess{
		AccessToken: "xoxb-new", TeamID: "T2", TeamName: "Globex", UserID: "U9",
		BotUserID: "UBOT", Scopes: []string{"chat:write", "commands"}, EnterpriseID: "E1", IsEnterpriseInstall: false,
	}

	r := h.srv.Handle(context.Background(), Request{Method: "GET", Path: PathAuth, QueryParams: map[string]string{"code": "c"}})
	if h.slack.OAuthRedirectURI != "https://api.example.com/v1/auth" {
		t.Errorf("redirect_uri sent to oauth.v2.access = %q", h.slack.OAuthRedirectURI)
	}
	if r.StatusCode != 302 || r.Headers["Location"] != "https://example.com/registered" {
		t.Fatalf("resp = %+v", r)
	}
	team := h.store.Teams["T2"]
	if team.BotAccessToken != "xoxb-new" || team.Name != "Globex" || team.InstalledByUserID != "U9" || team.BotUserID != "UBOT" ||
		len(team.Scopes) != 2 || team.EnterpriseID != "E1" || !team.CreatedAt.Equal(now) || team.UpdatedAt == nil || !team.UpdatedAt.Equal(now) || !team.Installed() {
		t.Errorf("team = %+v", team)
	}
	if got := h.slack.PostedTo("U9"); len(got) != 1 || got[0] != welcomeMessage {
		t.Errorf("welcome = %v", got)
	}
}

func TestInstallAndPingAndNotFound(t *testing.T) {
	h := newHarness(t)
	r := h.srv.Handle(context.Background(), Request{Method: "GET", Path: PathInstall})
	want := "https://slack.com/oauth/v2/authorize?client_id=123.456&redirect_uri=https%3A%2F%2Fapi.example.com%2Fv1%2Fauth&scope=app_mentions%3Aread%2Cchannels%3Aread%2Cchat%3Awrite%2Ccommands%2Cgroups%3Aread%2Cim%3Ahistory%2Cusers%3Aread"
	if r.StatusCode != 302 || r.Headers["Location"] != want {
		t.Errorf("install Location = %q\nwant %q", r.Headers["Location"], want)
	}
	if r := h.srv.Handle(context.Background(), Request{Method: "GET", Path: PathPing}); r.StatusCode != 200 {
		t.Errorf("ping = %+v", r)
	}
	if r := h.srv.Handle(context.Background(), Request{Method: "GET", Path: "/nope"}); r.StatusCode != 404 {
		t.Errorf("unknown = %+v", r)
	}
}
