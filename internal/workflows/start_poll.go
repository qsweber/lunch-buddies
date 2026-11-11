package workflows

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"slices"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/slack"
)

// PollInput is the input of PreparePoll, FormGroups and NotifyFailure.
type PollInput struct {
	CallbackID string `json:"callback_id"`
}

// PrepareOutput feeds the StartPoll Map state.
type PrepareOutput struct {
	CallbackID string   `json:"callback_id"`
	UserIDs    []string `json:"user_ids"`
}

// PreparePoll resolves the poll's channel, opens the poll (claiming the channel's
// ACTIVE_POLL pointer), and returns the channel members to DM. It is safe to re-run: a poll
// that is already OPEN skips straight to listing members, and a REJECTED one returns no users.
func (d Deps) PreparePoll(ctx context.Context, in PollInput) (PrepareOutput, error) {
	out := PrepareOutput{CallbackID: in.CallbackID, UserIDs: []string{}}

	poll, err := d.Repositories.Polls.GetPoll(ctx, in.CallbackID)
	if err != nil {
		return out, err
	}
	if poll == nil {
		return out, fmt.Errorf("poll %s not found", in.CallbackID)
	}
	team, err := d.loadTeam(ctx, poll.TeamID)
	if err != nil {
		return out, err
	}

	if poll.State == repositories.StateRequested {
		rejected, err := d.openPoll(ctx, team, poll)
		if err != nil || rejected {
			return out, err
		}
		if poll, err = d.Repositories.Polls.GetPoll(ctx, in.CallbackID); err != nil {
			return out, err
		}
	}

	if poll.State != repositories.StateOpen {
		slog.Info("poll is not open; nothing to send", "callback_id", poll.CallbackID, "state", poll.State)
		return out, nil
	}

	members, err := d.Slack.ConversationMembers(ctx, team.BotAccessToken, poll.ChannelID)
	if err != nil {
		return out, err
	}
	out.UserIDs = members
	return out, nil
}

// openPoll moves a REQUESTED poll to OPEN or REJECTED. It returns rejected=true if the poll
// was rejected (the creator has been told why).
func (d Deps) openPoll(ctx context.Context, team *repositories.Team, poll *repositories.Poll) (bool, error) {
	reject := func(reason, message string) (bool, error) {
		if err := d.dm(ctx, team.BotAccessToken, poll.CreatedByUserID, message); err != nil {
			return false, err
		}
		err := d.Repositories.Polls.RejectPoll(ctx, poll.CallbackID, reason)
		if err != nil && !errors.Is(err, repositories.ErrInvalidTransition) {
			return false, err
		}
		slog.Info("poll rejected", "callback_id", poll.CallbackID, "reason", reason)
		return true, nil
	}

	channelID := poll.ChannelID
	if channelID == "" {
		channel, err := d.Slack.FindChannelByName(ctx, team.BotAccessToken, polls.DefaultChannelName)
		if err != nil {
			return false, err
		}
		if channel == nil {
			return reject("default_channel_not_found", polls.DefaultChannelNotFound)
		}
		members, err := d.Slack.ConversationMembers(ctx, team.BotAccessToken, channel.ID)
		if err != nil {
			return false, err
		}
		if !slices.Contains(members, poll.CreatedByUserID) {
			return reject("user_not_in_default_channel", polls.UserNotInDefaultChannel(channel.ID, channel.Name))
		}
		channelID = channel.ID
	}

	err := d.Repositories.Polls.OpenPoll(ctx, *poll, channelID, d.Now())
	switch {
	case errors.Is(err, repositories.ErrActivePollExists):
		return reject("active_poll_exists", polls.MsgActivePollExists)
	case errors.Is(err, repositories.ErrInvalidTransition):
		// A concurrent run already moved it on; the caller re-reads the poll.
		return false, nil
	}
	return false, err
}

// PollUserInput is one item of the StartPoll Map.
type PollUserInput struct {
	CallbackID string `json:"callback_id"`
	UserID     string `json:"user_id"`
}

// PollUser DMs one user the poll buttons, unless the poll is no longer open or the user was
// already sent it (a retry after a crash between posting and recording can still double-send;
// see the design doc §6).
func (d Deps) PollUser(ctx context.Context, in PollUserInput) error {
	poll, err := d.Repositories.Polls.GetPoll(ctx, in.CallbackID)
	if err != nil {
		return err
	}
	if poll == nil || poll.State != repositories.StateOpen {
		return nil
	}
	sent, err := d.Repositories.Polls.GetRecipient(ctx, in.CallbackID, in.UserID)
	if err != nil || sent != nil {
		return err
	}
	team, err := d.loadTeam(ctx, poll.TeamID)
	if err != nil {
		return err
	}
	ts, err := d.Slack.PostMessage(ctx, team.BotAccessToken, slack.Message{
		Channel:     in.UserID,
		Text:        polls.MsgPollQuestion,
		Attachments: polls.PollAttachments(poll.CallbackID, poll.Choices),
		AsUser:      true,
	})
	if errors.Is(err, slack.ErrChannelNotFound) {
		slog.Warn("could not DM user; channel not found", "user", in.UserID)
		return nil
	}
	if err != nil {
		return err
	}
	return d.Repositories.Polls.MarkRecipientSent(ctx, in.CallbackID, in.UserID, ts, d.Now())
}
