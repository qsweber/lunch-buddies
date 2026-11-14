package server

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/url"
	"regexp"
	"strings"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/slack"
)

// eventCallback is the subset of a Slack Events API request we use.
type eventCallback struct {
	Token     string `json:"token"`
	Type      string `json:"type"`
	Challenge string `json:"challenge"`
	TeamID    string `json:"team_id"`
	Event     struct {
		Type    string `json:"type"`
		Channel string `json:"channel"`
		User    string `json:"user"`
		Text    string `json:"text"`
		// Tokens is set on tokens_revoked events.
		Tokens struct {
			Bot []string `json:"bot"`
		} `json:"tokens"`
	} `json:"event"`
}

type botMention struct {
	TeamID    string
	ChannelID string
	UserID    string
	Text      string
}

var mentionPattern = regexp.MustCompile(`.*<@.+> (.*)`)

// Bot handles Events API callbacks (app mentions and DMs).
func (s *ServerImpl) Bot(ctx context.Context, req Request) Response {
	body := req.Body
	if strings.HasPrefix(req.Headers["content-type"], "application/x-www-form-urlencoded") {
		form, err := url.ParseQuery(body)
		if err == nil && form.Get("payload") != "" {
			body = form.Get("payload")
		}
	}
	var cb eventCallback
	if err := json.Unmarshal([]byte(body), &cb); err != nil {
		return errorResponse(400, fmt.Errorf("invalid event: %w", err))
	}
	if err := s.sc.Verifier.Verify(req.Headers, req.Body, cb.Token); err != nil {
		return errorResponse(401, err)
	}
	if cb.Type == "url_verification" {
		return jsonResponse(200, map[string]string{"challenge": cb.Challenge})
	}
	// Slack redelivers events it thinks we missed. The first delivery already did the work,
	// so acknowledge retries without acting (design P6).
	if req.Headers["x-slack-retry-num"] != "" {
		return Response{StatusCode: 200, Body: "ok"}
	}

	// Uninstalls: app_uninstalled, or tokens_revoked including the bot token. Either way the
	// stored token is dead, so record the uninstall and drop it.
	if cb.Event.Type == "app_uninstalled" || (cb.Event.Type == "tokens_revoked" && len(cb.Event.Tokens.Bot) > 0) {
		if err := s.sc.Repositories.Teams.MarkTeamUninstalled(ctx, cb.TeamID, s.sc.Now()); err != nil {
			return errorResponse(500, err)
		}
		slog.Info("team uninstalled", "team_id", cb.TeamID, "event", cb.Event.Type)
		return Response{StatusCode: 200, Body: "ok"}
	}

	team, err := s.sc.Repositories.Teams.GetTeam(ctx, cb.TeamID)
	if err != nil {
		return errorResponse(500, err)
	}
	if team == nil || !team.Installed() {
		return errorResponse(403, fmt.Errorf("your team is not authorized for this app"))
	}

	// Commands arrive only as @-mentions (the app no longer requests im:history, so it doesn't
	// receive direct messages).
	if cb.Event.Type != "app_mention" {
		return Response{StatusCode: 200, Body: "ok"}
	}
	mention := parseEvent(cb)
	if err := s.handleMention(ctx, team, mention); err != nil {
		return errorResponse(500, err)
	}
	return Response{StatusCode: 200, Body: "ok"}
}

func parseEvent(cb eventCallback) botMention {
	return botMention{TeamID: cb.TeamID, ChannelID: cb.Event.Channel, UserID: cb.Event.User, Text: cb.Event.Text}
}

// parseCommand returns the first word after the mention and the rest, or ok=false if the
// message isn't a command for us. Ported from bot._parse_message.
func parseCommand(m botMention) (first, rest string, ok bool) {
	match := mentionPattern.FindStringSubmatch(m.Text)
	if match == nil {
		return "", "", false
	}
	cleaned := strings.Trim(strings.TrimSpace(strings.ToLower(match[1])), ".")
	words := strings.Fields(cleaned)
	if len(words) == 0 {
		return "", "", false
	}
	return words[0], strings.TrimSpace(strings.Join(words[1:], " ")), true
}

func (s *ServerImpl) handleMention(ctx context.Context, team *repositories.Team, m botMention) error {
	first, rest, ok := parseCommand(m)
	if !ok {
		return nil
	}
	slog.Info("bot command", "team", team.TeamID, "command", first)

	var reply string
	var err error
	switch first {
	case "create":
		reply, err = s.createPoll(ctx, team.TeamID, m.ChannelID, m.UserID, rest)
	case "close":
		reply, err = s.closePoll(ctx, team, m.ChannelID, m.UserID, rest)
	case "help":
		reply = polls.AppExplanation
	default:
		return nil
	}
	if err != nil {
		return err
	}
	if reply == "" {
		return nil
	}
	_, err = s.sc.Slack.PostMessage(ctx, team.BotAccessToken, slack.Message{Channel: m.ChannelID, Text: reply, AsUser: true})
	return err
}
