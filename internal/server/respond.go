package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"strconv"
	"time"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
)

// interactivePayload is the subset of Slack's legacy interactive-message payload we use.
type interactivePayload struct {
	Token           string         `json:"token"`
	CallbackID      string         `json:"callback_id"`
	ActionTS        string         `json:"action_ts"`
	OriginalMessage map[string]any `json:"original_message"`
	Team            struct {
		ID string `json:"id"`
	} `json:"team"`
	User struct {
		ID string `json:"id"`
	} `json:"user"`
	Actions []struct {
		Value string `json:"value"`
	} `json:"actions"`
}

// RespondToPoll handles a poll button click: it records the answer (only while the poll is
// OPEN) and returns the original message with a confirmation appended.
func (s *ServerImpl) RespondToPoll(ctx context.Context, req Request) Response {
	form, err := url.ParseQuery(req.Body)
	if err != nil {
		return errorResponse(400, err)
	}
	var payload interactivePayload
	if err := json.Unmarshal([]byte(form.Get("payload")), &payload); err != nil {
		return errorResponse(400, fmt.Errorf("invalid payload: %w", err))
	}
	if err := s.sc.Verifier.Verify(req.Headers, req.Body, payload.Token); err != nil {
		return errorResponse(401, err)
	}
	if len(payload.Actions) == 0 {
		return errorResponse(400, errors.New("payload has no actions"))
	}

	poll, err := s.sc.Repositories.Polls.GetPoll(ctx, payload.CallbackID)
	if err != nil {
		return errorResponse(500, err)
	}
	if poll == nil || poll.TeamID != payload.Team.ID {
		return errorResponse(404, errors.New("poll not found"))
	}
	choice := polls.FindChoice(poll.Choices, payload.Actions[0].Value)
	if choice == nil {
		return errorResponse(400, errors.New("unknown choice"))
	}

	// When the user clicked, per Slack (epoch seconds with a fraction); now if absent.
	createdAt := s.sc.Now()
	if actionTS, err := strconv.ParseFloat(payload.ActionTS, 64); err == nil && actionTS > 0 {
		createdAt = time.UnixMilli(int64(actionTS * 1000))
	}

	confirmation := polls.ResponseReceived(*choice)
	err = s.sc.Repositories.Polls.RecordResponse(ctx, repositories.PollResponse{
		CallbackID: poll.CallbackID,
		UserID:     payload.User.ID,
		Response:   choice.Key,
		CreatedAt:  repositories.At(createdAt),
	})
	if errors.Is(err, repositories.ErrPollNotOpen) {
		confirmation = polls.MsgPollClosedForResponse
	} else if err != nil {
		return errorResponse(500, err)
	}

	message := payload.OriginalMessage
	if message == nil {
		message = map[string]any{}
	}
	attachments, _ := message["attachments"].([]any)
	message["attachments"] = append(attachments, map[string]any{"text": confirmation})
	return jsonResponse(200, message)
}
