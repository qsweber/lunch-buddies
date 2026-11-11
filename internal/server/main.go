// Package server is the HTTP API that Slack calls. Per the design, handlers only verify the
// request, read/write the records table and reply; fan-out work happens downstream via the
// DynamoDB stream and Step Functions.
package server

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/url"
	"strings"

	"github.com/qsweber/lunch-buddies/internal/repositories"
)

type Request struct {
	Method      string
	Path        string
	Headers     map[string]string // lowercase names
	QueryParams map[string]string
	RawQuery    string // the query string as received, for forwarding
	Body        string
}

type Response struct {
	StatusCode int
	Body       string
	Headers    map[string]string
}

type Server interface {
	Handle(ctx context.Context, req Request) Response
}

type ServerImpl struct {
	sc ServiceContext
}

func New(sc ServiceContext) Server {
	return &ServerImpl{sc: sc}
}

// Routes, versioned under /v1 as in go-template. (The Python app used /api/v0/...; the Slack
// app config is re-entered at cutover anyway because the host changes.)
const (
	PathPing       = "/v1/ping"
	PathCreatePoll = "/v1/poll/create"
	PathRespond    = "/v1/poll"
	PathClosePoll  = "/v1/poll/close"
	PathHelp       = "/v1/help"
	PathInstall    = "/v1/install"
	PathAuth       = "/v1/auth"
	PathBot        = "/v1/bot"
)

func (s *ServerImpl) Handle(ctx context.Context, req Request) Response {
	if s.sc.Forwarder != nil {
		if resp, ok := s.sc.Forwarder.forward(ctx, req); ok {
			return resp
		}
	}

	route := req.Method + " " + req.Path
	var resp Response
	switch route {
	case "GET " + PathPing:
		resp = jsonResponse(200, map[string]string{"status": "ok"})
	case "POST " + PathCreatePoll:
		resp = s.CreatePollCommand(ctx, req)
	case "POST " + PathRespond:
		resp = s.RespondToPoll(ctx, req)
	case "POST " + PathClosePoll:
		resp = s.ClosePollCommand(ctx, req)
	case "POST " + PathHelp:
		resp = s.Help(ctx, req)
	case "GET " + PathInstall:
		resp = redirect(s.sc.Config.AuthURL)
	case "GET " + PathAuth:
		resp = s.Auth(ctx, req)
	case "POST " + PathBot:
		resp = s.Bot(ctx, req)
	default:
		resp = errorResponse(404, errors.New("route not found"))
	}
	slog.Info("request", "method", req.Method, "path", req.Path, "status", resp.StatusCode)
	return resp
}

// slashCommand is the form Slack posts for slash commands.
type slashCommand struct {
	Token  string
	TeamID string
	UserID string
	Text   string
}

func parseSlashCommand(body string) (slashCommand, error) {
	form, err := url.ParseQuery(body)
	if err != nil {
		return slashCommand{}, err
	}
	return slashCommand{
		Token:  form.Get("token"),
		TeamID: form.Get("team_id"),
		UserID: form.Get("user_id"),
		Text:   form.Get("text"),
	}, nil
}

// authorize verifies the request came from Slack and the team is installed.
func (s *ServerImpl) authorize(ctx context.Context, req Request, token, teamID string) (*repositories.Team, *Response) {
	if err := s.sc.Verifier.Verify(req.Headers, req.Body, token); err != nil {
		r := errorResponse(401, err)
		return nil, &r
	}
	team, err := s.sc.Repositories.Teams.GetTeam(ctx, teamID)
	if err != nil {
		r := errorResponse(500, err)
		return nil, &r
	}
	if team == nil {
		r := errorResponse(403, errors.New("your team is not authorized for this app"))
		return nil, &r
	}
	return team, nil
}

func (s *ServerImpl) Help(ctx context.Context, req Request) Response {
	cmd, err := parseSlashCommand(req.Body)
	if err != nil {
		return errorResponse(400, err)
	}
	if _, errResp := s.authorize(ctx, req, cmd.Token, cmd.TeamID); errResp != nil {
		return *errResp
	}
	return textResponse(appExplanation())
}

func isHelp(text string) bool { return strings.ToLower(strings.TrimSpace(text)) == "help" }

func textResponse(text string) Response {
	return jsonResponse(200, map[string]string{"text": text})
}

func jsonResponse(status int, v any) Response {
	body, err := json.Marshal(v)
	if err != nil {
		return errorResponse(500, err)
	}
	return Response{StatusCode: status, Body: string(body), Headers: map[string]string{
		"Content-Type":                "application/json",
		"Access-Control-Allow-Origin": "*",
	}}
}

func redirect(location string) Response {
	return Response{StatusCode: 302, Headers: map[string]string{"Location": location}}
}

func errorResponse(status int, err error) Response {
	if status >= 500 {
		slog.Error("request failed", "status", status, "error", err)
	}
	body, _ := json.Marshal(map[string]string{"error": err.Error()})
	return Response{StatusCode: status, Body: string(body), Headers: map[string]string{"Content-Type": "application/json"}}
}
