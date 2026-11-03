package workflows

import (
	"context"
	"encoding/json"
	"fmt"
)

// Task names. The state machines put one in the "task" field of every Lambda payload, and
// one worker Lambda dispatches on it.
const (
	TaskPreparePoll   = "prepare-poll"
	TaskPollUser      = "poll-user"
	TaskFormGroups    = "form-groups"
	TaskNotifyGroup   = "notify-group"
	TaskNotifyFailure = "notify-failure"
)

// Handle is the worker Lambda's entry point for every Step Functions task.
//
// Task errors are returned unwrapped. aws-lambda-go reports the error's type name as
// errorType, and the state machines' Retry policies match on it (e.g. "RateLimitedError").
func (d Deps) Handle(ctx context.Context, payload json.RawMessage) (any, error) {
	var envelope struct {
		Task string `json:"task"`
	}
	if err := json.Unmarshal(payload, &envelope); err != nil {
		return nil, fmt.Errorf("invalid task payload: %w", err)
	}

	switch envelope.Task {
	case TaskPreparePoll:
		return run(ctx, payload, d.PreparePoll)
	case TaskPollUser:
		return run(ctx, payload, noOutput(d.PollUser))
	case TaskFormGroups:
		return run(ctx, payload, d.FormGroups)
	case TaskNotifyGroup:
		return run(ctx, payload, noOutput(d.NotifyGroup))
	case TaskNotifyFailure:
		return run(ctx, payload, noOutput(d.NotifyFailure))
	default:
		return nil, fmt.Errorf("unknown task %q", envelope.Task)
	}
}

func run[In, Out any](ctx context.Context, payload json.RawMessage, fn func(context.Context, In) (Out, error)) (any, error) {
	var in In
	if err := json.Unmarshal(payload, &in); err != nil {
		return nil, fmt.Errorf("invalid task input: %w", err)
	}
	out, err := fn(ctx, in)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func noOutput[In any](fn func(context.Context, In) error) func(context.Context, In) (struct{}, error) {
	return func(ctx context.Context, in In) (struct{}, error) { return struct{}{}, fn(ctx, in) }
}
