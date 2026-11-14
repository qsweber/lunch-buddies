package workflows

import (
	"context"
	"errors"
	"fmt"
	"log/slog"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/slack"
)

// FormGroupsOutput feeds the ClosePoll Map state.
type FormGroupsOutput struct {
	CallbackID string   `json:"callback_id"`
	GroupSKs   []string `json:"group_sks"`
}

// FormGroups splits the closed poll's "yes" respondents into groups and persists them before
// anyone is notified. Groups are written in one transaction together with the poll's
// group_count, so a retry either finds every group (and reuses them) or none.
func (d Deps) FormGroups(ctx context.Context, in PollInput) (FormGroupsOutput, error) {
	out := FormGroupsOutput{CallbackID: in.CallbackID, GroupSKs: []string{}}

	collection, err := d.Repositories.Polls.GetPollCollection(ctx, in.CallbackID)
	if err != nil {
		return out, err
	}
	poll := collection.Poll
	if poll == nil {
		return out, fmt.Errorf("poll %s not found", in.CallbackID)
	}
	if poll.GroupCount != nil {
		return withGroups(out, collection.Groups), nil
	}
	if poll.State != repositories.StateClosed {
		slog.Info("poll is not closed; nothing to group", "callback_id", poll.CallbackID, "state", poll.State)
		return out, nil
	}

	responses := make([]polls.Response, len(collection.Responses))
	for i, r := range collection.Responses {
		responses[i] = polls.Response{UserID: r.UserID, ResponseKey: r.Response}
	}
	groups := polls.FormGroups(poll.Choices, responses, poll.GroupSize, d.Rand)

	stored, err := d.Repositories.Polls.SaveGroups(ctx, poll.CallbackID, groups)
	if errors.Is(err, repositories.ErrInvalidTransition) {
		// Another attempt saved groups first; use those.
		again, err := d.Repositories.Polls.GetPollCollection(ctx, in.CallbackID)
		if err != nil {
			return out, err
		}
		return withGroups(out, again.Groups), nil
	}
	if err != nil {
		return out, err
	}

	if len(collection.Responses) == 0 {
		team, err := d.loadTeam(ctx, poll.TeamID)
		if err != nil {
			return out, err
		}
		if err := d.dm(ctx, team.BotAccessToken, poll.ClosedByUserID, polls.MsgNoPollResponses); err != nil {
			slog.Error("failed to send no-responses DM", "error", err)
		}
	}
	return withGroups(out, stored), nil
}

func withGroups(out FormGroupsOutput, groups []repositories.Group) FormGroupsOutput {
	for _, g := range groups {
		out.GroupSKs = append(out.GroupSKs, g.SK)
	}
	return out
}

// NotifyGroupInput is one item of the ClosePoll Map.
type NotifyGroupInput struct {
	CallbackID string `json:"callback_id"`
	GroupSK    string `json:"group_sk"`
}

// NotifyGroup announces one group in the poll's channel, with a threaded follow-up naming who
// picks the location. Ported from notify_group.py (in-channel mode, which is now the only mode).
func (d Deps) NotifyGroup(ctx context.Context, in NotifyGroupInput) error {
	group, err := d.Repositories.Polls.GetGroup(ctx, in.CallbackID, in.GroupSK)
	if err != nil {
		return err
	}
	if group == nil {
		return fmt.Errorf("group %s/%s not found", in.CallbackID, in.GroupSK)
	}
	if group.NotifiedAt != 0 {
		return nil
	}
	poll, err := d.Repositories.Polls.GetPoll(ctx, in.CallbackID)
	if err != nil {
		return err
	}
	if poll == nil {
		return fmt.Errorf("poll %s not found", in.CallbackID)
	}
	team, err := d.loadTeam(ctx, poll.TeamID)
	if err != nil {
		return err
	}
	choice := polls.FindChoice(poll.Choices, group.ResponseKey)
	if choice == nil {
		return fmt.Errorf("poll %s has no choice %q", poll.CallbackID, group.ResponseKey)
	}

	if err := d.notifyInChannel(ctx, team, poll, *choice, group.UserIDs); err != nil {
		return err
	}
	return d.Repositories.Polls.MarkGroupNotified(ctx, in.CallbackID, in.GroupSK, d.Now())
}

func (d Deps) notifyInChannel(ctx context.Context, team *repositories.Team, poll *repositories.Poll, choice polls.Choice, userIDs []string) error {
	stillInChannel, err := d.Slack.ConversationMembers(ctx, team.BotAccessToken, poll.ChannelID)
	if err != nil {
		return err
	}
	include := polls.Intersect(stillInChannel, userIDs)
	if len(include) == 0 {
		slog.Info("nobody from the group is still in the channel", "callback_id", poll.CallbackID)
		return nil
	}
	ts, err := d.Slack.PostMessage(ctx, team.BotAccessToken, slack.Message{
		Channel: poll.ChannelID,
		Text:    polls.InChannelGroupMessage(choice, include),
		AsUser:  true,
	})
	if err != nil {
		return err
	}
	_, err = d.Slack.PostMessage(ctx, team.BotAccessToken, slack.Message{
		Channel:  poll.ChannelID,
		Text:     polls.PickLocationMessage(randomChoice(d.Rand, include)),
		ThreadTS: ts,
		AsUser:   true,
	})
	return err
}

// FailureInput is what the state machines' Catch passes to NotifyFailure.
type FailureInput struct {
	CallbackID string `json:"callback_id"`
	Workflow   string `json:"workflow"` // "start" or "close"
}

// NotifyFailure tells whoever started or closed the poll that it failed. It never returns
// an error, so it can't mask the original failure in the execution history.
func (d Deps) NotifyFailure(ctx context.Context, in FailureInput) error {
	poll, err := d.Repositories.Polls.GetPoll(ctx, in.CallbackID)
	if err != nil || poll == nil {
		slog.Error("NotifyFailure: poll not loaded", "callback_id", in.CallbackID, "error", err)
		return nil
	}
	team, err := d.loadTeam(ctx, poll.TeamID)
	if err != nil {
		slog.Error("NotifyFailure: team not loaded", "error", err)
		return nil
	}
	user := poll.CreatedByUserID
	if in.Workflow == "close" && poll.ClosedByUserID != "" {
		user = poll.ClosedByUserID
	}
	if err := d.dm(ctx, team.BotAccessToken, user, polls.MsgSomethingWentWrong); err != nil {
		slog.Error("NotifyFailure: DM failed", "error", err)
	}
	return nil
}
