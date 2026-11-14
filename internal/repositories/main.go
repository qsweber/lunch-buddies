// Package repositories is the single-table DynamoDB data layer. Every entity lives in the one
// "<stack>-records" table, distinguished by the shape of its partition key (pk) and sort key
// (sk). See docs/design/event-driven-single-table.md §4 for the full key design.
package repositories

import (
	"context"
	"errors"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
)

const (
	PartitionKeyAttribute = "pk"
	SortKeyAttribute      = "sk"
)

// DynamoDBAPI is the subset of the DynamoDB client the repositories use, so tests can
// substitute a fake. *dynamodb.Client satisfies it.
type DynamoDBAPI interface {
	PutItem(ctx context.Context, params *dynamodb.PutItemInput, optFns ...func(*dynamodb.Options)) (*dynamodb.PutItemOutput, error)
	GetItem(ctx context.Context, params *dynamodb.GetItemInput, optFns ...func(*dynamodb.Options)) (*dynamodb.GetItemOutput, error)
	UpdateItem(ctx context.Context, params *dynamodb.UpdateItemInput, optFns ...func(*dynamodb.Options)) (*dynamodb.UpdateItemOutput, error)
	Query(ctx context.Context, params *dynamodb.QueryInput, optFns ...func(*dynamodb.Options)) (*dynamodb.QueryOutput, error)
	TransactWriteItems(ctx context.Context, params *dynamodb.TransactWriteItemsInput, optFns ...func(*dynamodb.Options)) (*dynamodb.TransactWriteItemsOutput, error)
	BatchWriteItem(ctx context.Context, params *dynamodb.BatchWriteItemInput, optFns ...func(*dynamodb.Options)) (*dynamodb.BatchWriteItemOutput, error)
}

// Repositories groups the repositories the services depend on.
type Repositories struct {
	Teams TeamsRepository
	Polls PollsRepository
}

// New builds both repositories against one table.
func New(tableName string, client DynamoDBAPI) Repositories {
	return Repositories{
		Teams: NewTeamsRepository(tableName, client),
		Polls: NewPollsRepository(tableName, client),
	}
}

var (
	// ErrInvalidTransition means the poll was not in the state the operation requires.
	ErrInvalidTransition = errors.New("poll is not in the expected state")
	// ErrActivePollExists means another open poll already holds the channel's ACTIVE_POLL pointer.
	ErrActivePollExists = errors.New("there is already an active poll in this channel")
	// ErrPollNotOpen means a response or close targeted a poll that isn't OPEN.
	ErrPollNotOpen = errors.New("poll is not open")
)

func key(pk, sk string) map[string]types.AttributeValue {
	return map[string]types.AttributeValue{
		PartitionKeyAttribute: &types.AttributeValueMemberS{Value: pk},
		SortKeyAttribute:      &types.AttributeValueMemberS{Value: sk},
	}
}

func s(v string) types.AttributeValue { return &types.AttributeValueMemberS{Value: v} }
func n(v int64) types.AttributeValue  { return &types.AttributeValueMemberN{Value: fmt.Sprint(v)} }
func isConditionFailed(err error) bool {
	var c *types.ConditionalCheckFailedException
	return errors.As(err, &c)
}

// cancellationCodes returns the per-item cancellation codes of a failed transaction, or nil
// if err isn't a TransactionCanceledException.
func cancellationCodes(err error) []string {
	var tce *types.TransactionCanceledException
	if !errors.As(err, &tce) {
		return nil
	}
	codes := make([]string, len(tce.CancellationReasons))
	for i, r := range tce.CancellationReasons {
		if r.Code != nil {
			codes[i] = *r.Code
		}
	}
	return codes
}

const conditionalCheckFailed = "ConditionalCheckFailed"
