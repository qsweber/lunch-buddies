package server

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestForwardingModePassesRequestsThroughToLegacyAPI(t *testing.T) {
	var got struct {
		method, path, query, body, contentType, signature string
	}
	legacy := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		b, _ := io.ReadAll(r.Body)
		got.method, got.path, got.query, got.body = r.Method, r.URL.Path, r.URL.RawQuery, string(b)
		got.contentType, got.signature = r.Header.Get("Content-Type"), r.Header.Get("X-Slack-Signature")
		if r.URL.Path == "/production/api/v0/install" {
			w.Header().Set("Location", "https://slack.com/oauth")
			w.WriteHeader(302)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"text":"ok!"}`))
	}))
	defer legacy.Close()

	h := newHarness(t)
	h.srv.(*ServerImpl).sc.Forwarder = NewForwarder(legacy.URL + "/production/")

	resp := h.srv.Handle(context.Background(), Request{
		Method:  "POST",
		Path:    PathCreatePoll,
		Headers: map[string]string{"content-type": "application/x-www-form-urlencoded", "x-slack-signature": "v0=abc"},
		Body:    "token=t&text=1200",
	})
	if resp.StatusCode != 200 || resp.Body != `{"text":"ok!"}` || resp.Headers["Content-Type"] != "application/json" {
		t.Fatalf("resp = %+v", resp)
	}
	if got.method != "POST" || got.path != "/production/api/v0/poll/create" || got.body != "token=t&text=1200" ||
		got.contentType != "application/x-www-form-urlencoded" || got.signature != "v0=abc" {
		t.Errorf("legacy got %+v", got)
	}
	if len(h.store.Polls) != 0 {
		t.Error("forwarding mode must not write to the new table")
	}

	// Redirects reach the browser unfollowed, and query strings pass through.
	resp = h.srv.Handle(context.Background(), Request{Method: "GET", Path: PathInstall, RawQuery: "x=1"})
	if resp.StatusCode != 302 || resp.Headers["Location"] != "https://slack.com/oauth" || got.query != "x=1" {
		t.Errorf("install resp = %+v, query %q", resp, got.query)
	}

	// Ping is always served locally so deploy health checks work.
	if resp := h.srv.Handle(context.Background(), Request{Method: "GET", Path: PathPing}); resp.StatusCode != 200 || got.path == "/production/api/v0/ping" {
		t.Errorf("ping = %+v", resp)
	}
}

func TestForwardingModeReportsLegacyOutageAs502(t *testing.T) {
	h := newHarness(t)
	h.srv.(*ServerImpl).sc.Forwarder = NewForwarder("http://127.0.0.1:1")
	if resp := h.srv.Handle(context.Background(), Request{Method: "POST", Path: PathHelp, Headers: map[string]string{}}); resp.StatusCode != 502 {
		t.Errorf("resp = %+v", resp)
	}
}

func TestForwardingModeAnswersURLVerificationLocally(t *testing.T) {
	calls := 0
	legacy := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		w.WriteHeader(500)
	}))
	defer legacy.Close()

	h := newHarness(t)
	h.srv.(*ServerImpl).sc.Forwarder = NewForwarder(legacy.URL)

	body := `{"token":"` + token + `","type":"url_verification","challenge":"abc123"}`
	resp := h.srv.Handle(context.Background(), Request{Method: "POST", Path: PathBot, Headers: map[string]string{}, Body: body})
	if resp.StatusCode != 200 || resp.Body != `{"challenge":"abc123"}` || calls != 0 {
		t.Errorf("resp = %+v, legacy calls = %d", resp, calls)
	}

	// The challenge still has to pass request verification.
	bad := `{"token":"wrong","type":"url_verification","challenge":"abc123"}`
	if resp := h.srv.Handle(context.Background(), Request{Method: "POST", Path: PathBot, Headers: map[string]string{}, Body: bad}); resp.StatusCode != 401 {
		t.Errorf("unverified challenge = %+v", resp)
	}

	// Every other bot event is still forwarded.
	h.srv.Handle(context.Background(), Request{Method: "POST", Path: PathBot, Headers: map[string]string{}, Body: botEvent("<@UBOT> create", "C1")})
	if calls != 1 {
		t.Errorf("event_callback should be forwarded; legacy calls = %d", calls)
	}
}
