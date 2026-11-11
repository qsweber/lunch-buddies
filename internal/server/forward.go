package server

import (
	"context"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"time"
)

// Forwarding mode (temporary, for the production cutover; see design doc §8).
//
// While the Slack app's new URLs await Slack's review, the new API may start receiving
// production traffic at any moment. Until we choose to cut over, it passes every request
// through to the legacy Zappa API unchanged, so Slack's approval changes nothing visible.
// Cutover is deleting the legacy_forward_url parameter and restarting the Lambda.

// legacyPaths maps each /v1 route to the Python app's path. /v1/ping is always served locally
// so deploy health checks keep working.
var legacyPaths = map[string]string{
	PathCreatePoll: "/api/v0/poll/create",
	PathRespond:    "/api/v0/poll",
	PathClosePoll:  "/api/v0/poll/close",
	PathHelp:       "/api/v0/help",
	PathInstall:    "/api/v0/install",
	PathAuth:       "/api/v0/auth",
	PathBot:        "/api/v0/bot",
}

// forwardedRequestHeaders are passed through. The Python app authenticates with the
// verification token in the body, but the Slack headers are kept so nothing is lost.
var forwardedRequestHeaders = []string{
	"content-type",
	"x-slack-signature",
	"x-slack-request-timestamp",
	"x-slack-retry-num",
	"x-slack-retry-reason",
	"user-agent",
}

// forwardedResponseHeaders are returned to Slack. Location carries the /install and /auth
// redirects.
var forwardedResponseHeaders = []string{"Content-Type", "Location", "Access-Control-Allow-Origin"}

// Forwarder sends requests to the legacy API.
type Forwarder struct {
	// BaseURL is the legacy API including its stage, e.g.
	// https://ahlfhssbq3.execute-api.us-west-2.amazonaws.com/production
	BaseURL string
	Client  *http.Client
}

func NewForwarder(baseURL string) *Forwarder {
	return &Forwarder{
		BaseURL: strings.TrimRight(baseURL, "/"),
		// Don't follow redirects: /install and /auth answer with a 302 that must reach the
		// browser as-is.
		Client: &http.Client{
			Timeout:       10 * time.Second,
			CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse },
		},
	}
}

func (f *Forwarder) forward(ctx context.Context, req Request) (Response, bool) {
	legacyPath, ok := legacyPaths[req.Path]
	if !ok {
		return Response{}, false
	}

	target := f.BaseURL + legacyPath
	if req.RawQuery != "" {
		target += "?" + req.RawQuery
	}
	out, err := http.NewRequestWithContext(ctx, req.Method, target, strings.NewReader(req.Body))
	if err != nil {
		return errorResponse(502, err), true
	}
	for _, name := range forwardedRequestHeaders {
		if v := req.Headers[name]; v != "" {
			out.Header.Set(name, v)
		}
	}

	resp, err := f.Client.Do(out)
	if err != nil {
		return errorResponse(502, err), true
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return errorResponse(502, err), true
	}

	headers := map[string]string{}
	for _, name := range forwardedResponseHeaders {
		if v := resp.Header.Get(name); v != "" {
			headers[name] = v
		}
	}
	slog.Info("forwarded to legacy API", "path", req.Path, "legacy_path", legacyPath, "status", resp.StatusCode)
	return Response{StatusCode: resp.StatusCode, Body: string(body), Headers: headers}, true
}
