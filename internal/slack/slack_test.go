package slack

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestClient(t *testing.T, handler http.HandlerFunc) *Client {
	t.Helper()
	srv := httptest.NewServer(handler)
	t.Cleanup(srv.Close)
	c := New()
	c.BaseURL = srv.URL + "/"
	return c
}

func TestPostMessageSendsJSONWithBearerToken(t *testing.T) {
	c := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/chat.postMessage" || r.Header.Get("Authorization") != "Bearer xoxb" {
			t.Errorf("path=%s auth=%s", r.URL.Path, r.Header.Get("Authorization"))
		}
		var msg Message
		body, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(body, &msg)
		if msg.Channel != "U1" || msg.Text != "hi" {
			t.Errorf("msg = %+v", msg)
		}
		_, _ = w.Write([]byte(`{"ok":true,"ts":"123.45"}`))
	})
	ts, err := c.PostMessage(context.Background(), "xoxb", Message{Channel: "U1", Text: "hi"})
	if err != nil || ts != "123.45" {
		t.Errorf("PostMessage = %q, %v", ts, err)
	}
}

func TestErrorsAreClassified(t *testing.T) {
	cases := []struct {
		status int
		body   string
		check  func(error) bool
	}{
		{200, `{"ok":false,"error":"channel_not_found"}`, func(err error) bool { return errors.Is(err, ErrChannelNotFound) }},
		{200, `{"ok":false,"error":"ratelimited"}`, func(err error) bool { var r *RateLimitedError; return errors.As(err, &r) }},
		{429, ``, func(err error) bool {
			var r *RateLimitedError
			return errors.As(err, &r) && r.RetryAfter.Seconds() == 7
		}},
		{200, `{"ok":false,"error":"not_authed"}`, func(err error) bool { var a *APIError; return errors.As(err, &a) && a.Code == "not_authed" }},
	}
	for _, c := range cases {
		client := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Retry-After", "7")
			w.WriteHeader(c.status)
			_, _ = w.Write([]byte(c.body))
		})
		_, err := client.PostMessage(context.Background(), "t", Message{})
		if !c.check(err) {
			t.Errorf("status %d body %s: err = %v", c.status, c.body, err)
		}
	}
}

func TestConversationMembersPaginates(t *testing.T) {
	calls := 0
	c := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		_ = r.ParseForm()
		calls++
		if r.Form.Get("cursor") == "" {
			_, _ = w.Write([]byte(`{"ok":true,"members":["U1","U2"],"response_metadata":{"next_cursor":"abc"}}`))
			return
		}
		_, _ = w.Write([]byte(`{"ok":true,"members":["U3"],"response_metadata":{"next_cursor":""}}`))
	})
	members, err := c.ConversationMembers(context.Background(), "t", "C1")
	if err != nil || len(members) != 3 || calls != 2 {
		t.Errorf("members = %v, err = %v, calls = %d", members, err, calls)
	}
}

func TestFindChannelByName(t *testing.T) {
	c := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"ok":true,"channels":[{"id":"C1","name":"general"},{"id":"C2","name":"lunch_buddies"}]}`))
	})
	ch, err := c.FindChannelByName(context.Background(), "t", "lunch_buddies")
	if err != nil || ch == nil || ch.ID != "C2" {
		t.Errorf("FindChannelByName = %+v, %v", ch, err)
	}
	ch, err = c.FindChannelByName(context.Background(), "t", "missing")
	if err != nil || ch != nil {
		t.Errorf("FindChannelByName(missing) = %+v, %v", ch, err)
	}
}

func TestOAuthV2AccessParsesInstallDetails(t *testing.T) {
	c := newTestClient(t, func(w http.ResponseWriter, r *http.Request) {
		_ = r.ParseForm()
		if r.URL.Path != "/oauth.v2.access" || r.Form.Get("redirect_uri") != "https://x/v1/auth" || r.Form.Get("code") != "c" {
			t.Errorf("path=%s form=%v", r.URL.Path, r.Form)
		}
		_, _ = w.Write([]byte(`{"ok":true,"access_token":"xoxb","scope":"chat:write,commands","bot_user_id":"UBOT",
			"team":{"id":"T1","name":"Acme"},"enterprise":{"id":"E1","name":"Org"},"is_enterprise_install":false,
			"authed_user":{"id":"U9"}}`))
	})
	got, err := c.OAuthV2Access(context.Background(), "id", "secret", "c", "https://x/v1/auth")
	if err != nil {
		t.Fatal(err)
	}
	if got.AccessToken != "xoxb" || got.TeamID != "T1" || got.UserID != "U9" || got.BotUserID != "UBOT" ||
		len(got.Scopes) != 2 || got.Scopes[1] != "commands" || got.EnterpriseID != "E1" || got.IsEnterpriseInstall {
		t.Errorf("access = %+v", got)
	}
}
