package server

import (
	"context"
	"errors"
	"fmt"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
)

func appExplanation() string { return polls.AppExplanation }

// CreatePollCommand handles /lunch_buddies_create. The channel is resolved downstream.
func (s *ServerImpl) CreatePollCommand(ctx context.Context, req Request) Response {
	cmd, err := parseSlashCommand(req.Body)
	if err != nil {
		return errorResponse(400, err)
	}
	team, errResp := s.authorize(ctx, req, cmd.Token, cmd.TeamID)
	if errResp != nil {
		return *errResp
	}
	text, err := s.createPoll(ctx, team.TeamID, "", cmd.UserID, cmd.Text)
	if err != nil {
		return errorResponse(500, err)
	}
	return textResponse(text)
}

// createPoll validates the text and writes a REQUESTED poll. It returns the reply text.
// channelID is empty for the slash command; PreparePoll then uses #lunch_buddies.
func (s *ServerImpl) createPoll(ctx context.Context, teamID, channelID, userID, text string) (string, error) {
	if isHelp(text) {
		return polls.CreatePollHelp, nil
	}
	choices, groupSize, err := polls.ParseText(text)
	if err != nil {
		return fmt.Sprintf("Failed: %s", err), nil
	}
	err = s.sc.Repositories.Polls.CreateRequestedPoll(ctx, repositories.Poll{
		CallbackID:      s.sc.NewID(),
		TeamID:          teamID,
		ChannelID:       channelID,
		CreatedByUserID: userID,
		CreatedAt:       repositories.At(s.sc.Now()),
		Choices:         choices,
		GroupSize:       groupSize,
		RequestedText:   text,
	})
	if err != nil {
		return "", err
	}
	return polls.MsgOK, nil
}

// ClosePollCommand handles /lunch_buddies_close.
func (s *ServerImpl) ClosePollCommand(ctx context.Context, req Request) Response {
	cmd, err := parseSlashCommand(req.Body)
	if err != nil {
		return errorResponse(400, err)
	}
	team, errResp := s.authorize(ctx, req, cmd.Token, cmd.TeamID)
	if errResp != nil {
		return *errResp
	}
	text, err := s.closePoll(ctx, team, "", cmd.UserID, cmd.Text)
	if err != nil {
		return errorResponse(500, err)
	}
	return textResponse(text)
}

// closePoll moves the channel's open poll to CLOSED. The ClosePoll workflow, started by the
// stream, does the grouping. Unlike the Python app, "not found" and "already closed" are
// answered inline instead of by DM.
func (s *ServerImpl) closePoll(ctx context.Context, team *repositories.Team, channelID, userID, text string) (string, error) {
	if isHelp(text) {
		return polls.ClosePollHelp, nil
	}

	active, msg, err := s.resolveActivePoll(ctx, team, channelID)
	if err != nil || active == nil {
		return msg, err
	}

	err = s.sc.Repositories.Polls.ClosePoll(ctx, *active, userID, s.sc.Now())
	if errors.Is(err, repositories.ErrPollNotOpen) {
		return polls.MsgPollAlreadyClosed, nil
	}
	if err != nil {
		return "", err
	}
	return polls.MsgOK, nil
}

// resolveActivePoll finds the poll to close. With a channel (bot mention) it's that
// channel's pointer. Without one (slash command): the team's only open poll; if there are
// several, the one in #lunch_buddies (the channel the slash command polls).
func (s *ServerImpl) resolveActivePoll(ctx context.Context, team *repositories.Team, channelID string) (*repositories.ActivePoll, string, error) {
	if channelID != "" {
		active, err := s.sc.Repositories.Polls.GetActivePoll(ctx, team.TeamID, channelID)
		if err != nil {
			return nil, "", err
		}
		if active == nil {
			return nil, polls.MsgNoPollFound, nil
		}
		return active, "", nil
	}

	all, err := s.sc.Repositories.Polls.ListActivePolls(ctx, team.TeamID)
	if err != nil {
		return nil, "", err
	}
	switch len(all) {
	case 0:
		return nil, polls.MsgNoPollFound, nil
	case 1:
		return &all[0], "", nil
	}
	channel, err := s.sc.Slack.FindChannelByName(ctx, team.BotAccessToken, polls.DefaultChannelName)
	if err != nil {
		return nil, "", err
	}
	if channel != nil {
		for i := range all {
			if all[i].ChannelID == channel.ID {
				return &all[i], "", nil
			}
		}
	}
	return nil, polls.MsgMultipleActivePolls, nil
}
