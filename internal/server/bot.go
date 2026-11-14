package server

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/url"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

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
		Subtype string `json:"subtype"`
		Channel string `json:"channel"`
		User    string `json:"user"`
		BotID   string `json:"bot_id"`
		Text    string `json:"text"`
		Message struct {
			Type string `json:"type"`
			User string `json:"user"`
			Text string `json:"text"`
		} `json:"message"`
		// Tokens is set on tokens_revoked events.
		Tokens struct {
			Bot []string `json:"bot"`
		} `json:"tokens"`
	} `json:"event"`
}

type botMention struct {
	TeamID      string
	ChannelID   string
	UserID      string
	Text        string
	MessageType string
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

	mention := parseEvent(cb)
	if err := s.handleMention(ctx, team, mention); err != nil {
		return errorResponse(500, err)
	}
	return Response{StatusCode: 200, Body: "ok"}
}

func parseEvent(cb eventCallback) botMention {
	if cb.Event.Subtype == "message_changed" {
		return botMention{TeamID: cb.TeamID, ChannelID: cb.Event.Channel, UserID: cb.Event.Message.User, Text: cb.Event.Message.Text, MessageType: cb.Event.Message.Type}
	}
	user := cb.Event.User
	if user == "" {
		user = cb.Event.BotID
	}
	return botMention{TeamID: cb.TeamID, ChannelID: cb.Event.Channel, UserID: user, Text: cb.Event.Text, MessageType: cb.Event.Type}
}

// parseCommand returns the first word and the rest, or ok=false if the message isn't a
// command for us. Ported from bot._parse_message.
func parseCommand(m botMention) (first, rest string, ok bool) {
	match := mentionPattern.FindStringSubmatch(m.Text)
	if match == nil && m.MessageType == "app_mention" {
		return "", "", false
	}
	text := m.Text
	if match != nil {
		text = match[1]
	}
	cleaned := strings.Trim(strings.TrimSpace(strings.ToLower(text)), ".")
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
	case "summary":
		reply, err = s.summary(ctx, team, m.UserID, rest)
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

var digitsPattern = regexp.MustCompile(`([0-9]+)`)

// summary lists the groups of each poll in the lookback window (default 7 days).
func (s *ServerImpl) summary(ctx context.Context, team *repositories.Team, userID, rest string) (string, error) {
	days := 7
	if m := digitsPattern.FindStringSubmatch(rest); m != nil {
		days, _ = strconv.Atoi(m[1])
	}
	pollList, err := s.sc.Repositories.Polls.ListPollsForTeam(ctx, team.TeamID, s.sc.Now().Add(-time.Duration(days)*24*time.Hour))
	if err != nil {
		return "", err
	}
	if len(pollList) == 0 {
		return "", nil
	}

	loc := time.UTC
	if user, err := s.sc.Slack.UserInfo(ctx, team.BotAccessToken, userID); err == nil && user.TZ != "" {
		if l, err := time.LoadLocation(user.TZ); err == nil {
			loc = l
		}
	}

	var sections []string
	for _, p := range pollList {
		collection, err := s.sc.Repositories.Polls.GetPollCollection(ctx, p.CallbackID)
		if err != nil {
			return "", err
		}
		if len(collection.Groups) == 0 {
			continue
		}
		sort.Slice(collection.Groups, func(i, j int) bool { return collection.Groups[i].SK < collection.Groups[j].SK })
		lines := []string{fmt.Sprintf("*%s: started by* <@%s>",
			p.CreatedAt.In(loc).Format("January 02, 2006"), p.CreatedByUserID)}
		for _, g := range collection.Groups {
			label := g.ResponseKey
			if c := polls.FindChoice(p.Choices, g.ResponseKey); c != nil {
				label = c.DisplayText
			}
			mentions := make([]string, len(g.UserIDs))
			for i, u := range g.UserIDs {
				mentions[i] = fmt.Sprintf("<@%s>", u)
			}
			lines = append(lines, fmt.Sprintf("%s: %s", label, strings.Join(mentions, " ")))
		}
		sections = append(sections, strings.Join(lines, "\n"))
	}
	return strings.Join(sections, "\n\n"), nil
}
