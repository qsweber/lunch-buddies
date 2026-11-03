package workflows

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/sfn"
	sfntypes "github.com/aws/aws-sdk-go-v2/service/sfn/types"

	"github.com/qsweber/lunch-buddies/internal/repositories"
)

// StepFunctionsAPI is the subset of the Step Functions client the router uses.
type StepFunctionsAPI interface {
	StartExecution(ctx context.Context, params *sfn.StartExecutionInput, optFns ...func(*sfn.Options)) (*sfn.StartExecutionOutput, error)
}

// Router starts a workflow for each poll state transition in a DynamoDB stream batch.
type Router struct {
	SFN                   StepFunctionsAPI
	StartPollStateMachine string
	ClosePollStateMachine string
}

// Transition is what a stream record means for the router.
type Transition int

const (
	TransitionNone Transition = iota
	TransitionPollRequested
	TransitionPollClosed
)

// Classify inspects a stream record. The event source mapping's filter criteria already
// drop everything else; this re-check keeps the router correct even without them.
func Classify(record events.DynamoDBEventRecord) (Transition, string) {
	newImage := record.Change.NewImage
	if attr(newImage, repositories.SortKeyAttribute) != repositories.PollSortKey {
		return TransitionNone, ""
	}
	callbackID := attr(newImage, "callback_id")
	newState := attr(newImage, "state")
	switch {
	case record.EventName == "INSERT" && newState == repositories.StateRequested:
		return TransitionPollRequested, callbackID
	case record.EventName == "MODIFY" && newState == repositories.StateClosed &&
		attr(record.Change.OldImage, "state") == repositories.StateOpen:
		return TransitionPollClosed, callbackID
	}
	return TransitionNone, ""
}

// Handle processes a batch, reporting per-record failures so only failed records are
// retried (ReportBatchItemFailures).
func (r Router) Handle(ctx context.Context, event events.DynamoDBEvent) (events.DynamoDBEventResponse, error) {
	var resp events.DynamoDBEventResponse
	for _, record := range event.Records {
		if err := r.handleRecord(ctx, record); err != nil {
			slog.Error("failed to start workflow", "event_id", record.EventID, "error", err)
			resp.BatchItemFailures = append(resp.BatchItemFailures, events.DynamoDBBatchItemFailure{
				ItemIdentifier: record.Change.SequenceNumber,
			})
		}
	}
	return resp, nil
}

func (r Router) handleRecord(ctx context.Context, record events.DynamoDBEventRecord) error {
	transition, callbackID := Classify(record)
	var stateMachine, name string
	switch transition {
	case TransitionPollRequested:
		stateMachine, name = r.StartPollStateMachine, "start-"+callbackID
	case TransitionPollClosed:
		stateMachine, name = r.ClosePollStateMachine, "close-"+callbackID
	default:
		return nil
	}

	input, err := json.Marshal(PollInput{CallbackID: callbackID})
	if err != nil {
		return err
	}
	_, err = r.SFN.StartExecution(ctx, &sfn.StartExecutionInput{
		StateMachineArn: aws.String(stateMachine),
		Name:            aws.String(name),
		Input:           aws.String(string(input)),
	})
	// The deterministic name makes a redelivered stream record a no-op.
	var exists *sfntypes.ExecutionAlreadyExists
	if errors.As(err, &exists) {
		slog.Info("execution already exists", "name", name)
		return nil
	}
	if err == nil {
		slog.Info("started workflow", "name", name)
	}
	return err
}

// attr returns a string attribute, or "" if absent or not a string (the events package's
// String() panics on a type mismatch).
func attr(image map[string]events.DynamoDBAttributeValue, name string) string {
	v, ok := image[name]
	if !ok || v.DataType() != events.DataTypeString {
		return ""
	}
	return v.String()
}
