package repositories

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"

	"github.com/qsweber/lunch-buddies/internal/polls"
)

// Poll states. See the state machine in the design doc §4.3.
const (
	StateRequested = "REQUESTED"
	StateOpen      = "OPEN"
	StateRejected  = "REJECTED"
	StateClosed    = "CLOSED"
	StateComplete  = "COMPLETE"
)

const (
	pollPartitionKeyPrefix = "POLL#"
	PollSortKey            = "POLL"
	activePollSKPrefix     = "ACTIVE_POLL#"
	recipientSKPrefix      = "RECIPIENT#"
	responseSKPrefix       = "RESPONSE#"
	groupSKPrefix          = "GROUP#"

	// ActivePollTTL is how long an open poll blocks a new poll in the same channel. This
	// preserves the Python behaviour where polls older than a day were ignored.
	ActivePollTTL = 24 * time.Hour

	// MaxGroupsPerPoll is bounded by the 100-item TransactWriteItems limit (99 groups plus
	// the poll update). At the default group size that's ~600 "yes" respondents per poll.
	MaxGroupsPerPoll = 99
)

func PollPartitionKey(callbackID string) string { return pollPartitionKeyPrefix + callbackID }
func ActivePollSortKey(channelID string) string { return activePollSKPrefix + channelID }
func RecipientSortKey(userID string) string     { return recipientSKPrefix + userID }
func ResponseSortKey(userID string) string      { return responseSKPrefix + userID }
func GroupSortKey(responseKey string, index int) string {
	return fmt.Sprintf("%s%s#%03d", groupSKPrefix, responseKey, index)
}

type Poll struct {
	PK              string         `dynamodbav:"pk"`
	SK              string         `dynamodbav:"sk"`
	CallbackID      string         `dynamodbav:"callback_id"`
	TeamID          string         `dynamodbav:"team_id"`
	ChannelID       string         `dynamodbav:"channel_id,omitempty"`
	CreatedByUserID string         `dynamodbav:"created_by_user_id"`
	CreatedAt       Timestamp      `dynamodbav:"created_at"`
	State           string         `dynamodbav:"state"`
	Choices         []polls.Choice `dynamodbav:"choices"`
	GroupSize       int            `dynamodbav:"group_size"`
	RequestedText   string         `dynamodbav:"requested_text,omitempty"`
	RejectionReason string         `dynamodbav:"rejection_reason,omitempty"`
	ClosedByUserID  string         `dynamodbav:"closed_by_user_id,omitempty"`
	ClosedAt        *Timestamp     `dynamodbav:"closed_at,omitempty"`
	GroupCount      *int           `dynamodbav:"group_count,omitempty"`
}

// WithKeys fills in the key attributes derived from the poll's fields.
func (p Poll) WithKeys() Poll {
	p.PK = PollPartitionKey(p.CallbackID)
	p.SK = PollSortKey
	return p
}

// ActivePoll is the per-channel pointer that enforces "one open poll per channel".
type ActivePoll struct {
	PK         string    `dynamodbav:"pk"`
	SK         string    `dynamodbav:"sk"`
	TeamID     string    `dynamodbav:"team_id"`
	ChannelID  string    `dynamodbav:"channel_id"`
	CallbackID string    `dynamodbav:"callback_id"`
	CreatedAt  Timestamp `dynamodbav:"created_at"`
}

func (a ActivePoll) WithKeys() ActivePoll {
	a.PK = TeamPartitionKey(a.TeamID)
	a.SK = ActivePollSortKey(a.ChannelID)
	return a
}

type Recipient struct {
	PK        string    `dynamodbav:"pk"`
	SK        string    `dynamodbav:"sk"`
	UserID    string    `dynamodbav:"user_id"`
	SentAt    Timestamp `dynamodbav:"sent_at"`
	MessageTS string    `dynamodbav:"message_ts,omitempty"`
}

type PollResponse struct {
	PK         string    `dynamodbav:"pk"`
	SK         string    `dynamodbav:"sk"`
	CallbackID string    `dynamodbav:"callback_id"`
	UserID     string    `dynamodbav:"user_id"`
	Response   string    `dynamodbav:"response"`
	CreatedAt  Timestamp `dynamodbav:"created_at"`
}

func (r PollResponse) WithKeys() PollResponse {
	r.PK = PollPartitionKey(r.CallbackID)
	r.SK = ResponseSortKey(r.UserID)
	return r
}

type Group struct {
	PK          string     `dynamodbav:"pk"`
	SK          string     `dynamodbav:"sk"`
	CallbackID  string     `dynamodbav:"callback_id"`
	ResponseKey string     `dynamodbav:"response_key"`
	UserIDs     []string   `dynamodbav:"user_ids"`
	NotifiedAt  *Timestamp `dynamodbav:"notified_at,omitempty"`
}

// PollCollection is everything stored under one poll's partition.
type PollCollection struct {
	Poll       *Poll
	Recipients []Recipient
	Responses  []PollResponse
	Groups     []Group
}

type PollsRepository interface {
	// CreateRequestedPoll writes a new poll in state REQUESTED.
	CreateRequestedPoll(ctx context.Context, poll Poll) error
	// GetPoll returns the poll (strongly consistent), or nil.
	GetPoll(ctx context.Context, callbackID string) (*Poll, error)
	// OpenPoll moves REQUESTED→OPEN and claims the channel's ACTIVE_POLL pointer atomically.
	// Returns ErrInvalidTransition or ErrActivePollExists.
	OpenPoll(ctx context.Context, poll Poll, channelID string, now time.Time) error
	// RejectPoll moves REQUESTED→REJECTED. Returns ErrInvalidTransition.
	RejectPoll(ctx context.Context, callbackID string, reason string) error
	// GetActivePoll returns the channel's ACTIVE_POLL pointer, or nil.
	GetActivePoll(ctx context.Context, teamID, channelID string) (*ActivePoll, error)
	// ListActivePolls returns every ACTIVE_POLL pointer for the team.
	ListActivePolls(ctx context.Context, teamID string) ([]ActivePoll, error)
	// ClosePoll moves OPEN→CLOSED and releases the pointer atomically. Returns ErrPollNotOpen.
	ClosePoll(ctx context.Context, active ActivePoll, closedByUserID string, now time.Time) error
	// RecordResponse writes the user's answer if the poll is OPEN. Returns ErrPollNotOpen.
	RecordResponse(ctx context.Context, response PollResponse) error
	// GetPollCollection returns the poll and all its child items (strongly consistent).
	GetPollCollection(ctx context.Context, callbackID string) (*PollCollection, error)
	// GetRecipient returns the recipient marker, or nil if the user hasn't been sent the poll.
	GetRecipient(ctx context.Context, callbackID, userID string) (*Recipient, error)
	// MarkRecipientSent records that the poll DM was delivered.
	MarkRecipientSent(ctx context.Context, callbackID, userID, messageTS string, now time.Time) error
	// SaveGroups atomically writes the groups and records the group count on the poll.
	// Returns the stored groups (with keys).
	SaveGroups(ctx context.Context, callbackID string, groups []polls.Group) ([]Group, error)
	// GetGroup returns one group, or nil.
	GetGroup(ctx context.Context, callbackID, groupSK string) (*Group, error)
	// MarkGroupNotified records that the group message was delivered.
	MarkGroupNotified(ctx context.Context, callbackID, groupSK string, now time.Time) error
}

type PollsRepositoryImpl struct {
	tableName string
	client    DynamoDBAPI
}

func NewPollsRepository(tableName string, client DynamoDBAPI) PollsRepository {
	return &PollsRepositoryImpl{tableName: tableName, client: client}
}

func (r *PollsRepositoryImpl) table() *string { return aws.String(r.tableName) }

func (r *PollsRepositoryImpl) CreateRequestedPoll(ctx context.Context, poll Poll) error {
	poll.State = StateRequested
	av, err := attributevalue.MarshalMap(poll.WithKeys())
	if err != nil {
		return err
	}
	_, err = r.client.PutItem(ctx, &dynamodb.PutItemInput{
		TableName:           r.table(),
		Item:                av,
		ConditionExpression: aws.String("attribute_not_exists(pk)"),
	})
	return err
}

func (r *PollsRepositoryImpl) GetPoll(ctx context.Context, callbackID string) (*Poll, error) {
	out, err := r.client.GetItem(ctx, &dynamodb.GetItemInput{
		TableName:      r.table(),
		Key:            key(PollPartitionKey(callbackID), PollSortKey),
		ConsistentRead: aws.Bool(true),
	})
	if err != nil || out.Item == nil {
		return nil, err
	}
	var p Poll
	if err := attributevalue.UnmarshalMap(out.Item, &p); err != nil {
		return nil, err
	}
	return &p, nil
}

func (r *PollsRepositoryImpl) OpenPoll(ctx context.Context, poll Poll, channelID string, now time.Time) error {
	pointer, err := attributevalue.MarshalMap(ActivePoll{
		TeamID:     poll.TeamID,
		ChannelID:  channelID,
		CallbackID: poll.CallbackID,
		CreatedAt:  poll.CreatedAt,
	}.WithKeys())
	if err != nil {
		return err
	}

	_, err = r.client.TransactWriteItems(ctx, &dynamodb.TransactWriteItemsInput{
		TransactItems: []types.TransactWriteItem{
			{Update: &types.Update{
				TableName:                r.table(),
				Key:                      key(PollPartitionKey(poll.CallbackID), PollSortKey),
				UpdateExpression:         aws.String("SET #state = :open, channel_id = :channel"),
				ConditionExpression:      aws.String("#state = :requested"),
				ExpressionAttributeNames: map[string]string{"#state": "state"},
				ExpressionAttributeValues: map[string]types.AttributeValue{
					":open":      s(StateOpen),
					":requested": s(StateRequested),
					":channel":   s(channelID),
				},
			}},
			{Put: &types.Put{
				TableName:           r.table(),
				Item:                pointer,
				ConditionExpression: aws.String("attribute_not_exists(pk) OR created_at < :cutoff"),
				ExpressionAttributeValues: map[string]types.AttributeValue{
					":cutoff": ts(now.Add(-ActivePollTTL)),
				},
			}},
		},
	})
	if codes := cancellationCodes(err); codes != nil {
		if len(codes) > 0 && codes[0] == conditionalCheckFailed {
			return ErrInvalidTransition
		}
		if len(codes) > 1 && codes[1] == conditionalCheckFailed {
			return ErrActivePollExists
		}
	}
	return err
}

func (r *PollsRepositoryImpl) RejectPoll(ctx context.Context, callbackID string, reason string) error {
	_, err := r.client.UpdateItem(ctx, &dynamodb.UpdateItemInput{
		TableName:                r.table(),
		Key:                      key(PollPartitionKey(callbackID), PollSortKey),
		UpdateExpression:         aws.String("SET #state = :rejected, rejection_reason = :reason"),
		ConditionExpression:      aws.String("#state = :requested"),
		ExpressionAttributeNames: map[string]string{"#state": "state"},
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":rejected":  s(StateRejected),
			":requested": s(StateRequested),
			":reason":    s(reason),
		},
	})
	if isConditionFailed(err) {
		return ErrInvalidTransition
	}
	return err
}

func (r *PollsRepositoryImpl) GetActivePoll(ctx context.Context, teamID, channelID string) (*ActivePoll, error) {
	out, err := r.client.GetItem(ctx, &dynamodb.GetItemInput{
		TableName:      r.table(),
		Key:            key(TeamPartitionKey(teamID), ActivePollSortKey(channelID)),
		ConsistentRead: aws.Bool(true),
	})
	if err != nil || out.Item == nil {
		return nil, err
	}
	var a ActivePoll
	if err := attributevalue.UnmarshalMap(out.Item, &a); err != nil {
		return nil, err
	}
	return &a, nil
}

func (r *PollsRepositoryImpl) ListActivePolls(ctx context.Context, teamID string) ([]ActivePoll, error) {
	var result []ActivePoll
	err := queryAll(ctx, r.client, &dynamodb.QueryInput{
		TableName:              r.table(),
		KeyConditionExpression: aws.String("pk = :pk AND begins_with(sk, :prefix)"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":pk":     s(TeamPartitionKey(teamID)),
			":prefix": s(activePollSKPrefix),
		},
		ConsistentRead: aws.Bool(true),
	}, func(item map[string]types.AttributeValue) error {
		var a ActivePoll
		if err := attributevalue.UnmarshalMap(item, &a); err != nil {
			return err
		}
		result = append(result, a)
		return nil
	})
	return result, err
}

func (r *PollsRepositoryImpl) ClosePoll(ctx context.Context, active ActivePoll, closedByUserID string, now time.Time) error {
	_, err := r.client.TransactWriteItems(ctx, &dynamodb.TransactWriteItemsInput{
		TransactItems: []types.TransactWriteItem{
			{Update: &types.Update{
				TableName:                r.table(),
				Key:                      key(PollPartitionKey(active.CallbackID), PollSortKey),
				UpdateExpression:         aws.String("SET #state = :closed, closed_by_user_id = :user, closed_at = :now"),
				ConditionExpression:      aws.String("#state = :open"),
				ExpressionAttributeNames: map[string]string{"#state": "state"},
				ExpressionAttributeValues: map[string]types.AttributeValue{
					":closed": s(StateClosed),
					":open":   s(StateOpen),
					":user":   s(closedByUserID),
					":now":    ts(now),
				},
			}},
			{Delete: &types.Delete{
				TableName:           r.table(),
				Key:                 key(TeamPartitionKey(active.TeamID), ActivePollSortKey(active.ChannelID)),
				ConditionExpression: aws.String("callback_id = :callback"),
				ExpressionAttributeValues: map[string]types.AttributeValue{
					":callback": s(active.CallbackID),
				},
			}},
		},
	})
	if cancellationCodes(err) != nil {
		return ErrPollNotOpen
	}
	return err
}

func (r *PollsRepositoryImpl) RecordResponse(ctx context.Context, response PollResponse) error {
	av, err := attributevalue.MarshalMap(response.WithKeys())
	if err != nil {
		return err
	}
	_, err = r.client.TransactWriteItems(ctx, &dynamodb.TransactWriteItemsInput{
		TransactItems: []types.TransactWriteItem{
			{ConditionCheck: &types.ConditionCheck{
				TableName:                r.table(),
				Key:                      key(PollPartitionKey(response.CallbackID), PollSortKey),
				ConditionExpression:      aws.String("#state = :open"),
				ExpressionAttributeNames: map[string]string{"#state": "state"},
				ExpressionAttributeValues: map[string]types.AttributeValue{
					":open": s(StateOpen),
				},
			}},
			{Put: &types.Put{TableName: r.table(), Item: av}},
		},
	})
	if codes := cancellationCodes(err); len(codes) > 0 && codes[0] == conditionalCheckFailed {
		return ErrPollNotOpen
	}
	return err
}

func (r *PollsRepositoryImpl) GetPollCollection(ctx context.Context, callbackID string) (*PollCollection, error) {
	c := &PollCollection{}
	err := queryAll(ctx, r.client, &dynamodb.QueryInput{
		TableName:              r.table(),
		KeyConditionExpression: aws.String("pk = :pk"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":pk": s(PollPartitionKey(callbackID)),
		},
		ConsistentRead: aws.Bool(true),
	}, func(item map[string]types.AttributeValue) error {
		sk, _ := item[SortKeyAttribute].(*types.AttributeValueMemberS)
		if sk == nil {
			return nil
		}
		switch {
		case sk.Value == PollSortKey:
			var p Poll
			if err := attributevalue.UnmarshalMap(item, &p); err != nil {
				return err
			}
			c.Poll = &p
		case strings.HasPrefix(sk.Value, recipientSKPrefix):
			var v Recipient
			if err := attributevalue.UnmarshalMap(item, &v); err != nil {
				return err
			}
			c.Recipients = append(c.Recipients, v)
		case strings.HasPrefix(sk.Value, responseSKPrefix):
			var v PollResponse
			if err := attributevalue.UnmarshalMap(item, &v); err != nil {
				return err
			}
			c.Responses = append(c.Responses, v)
		case strings.HasPrefix(sk.Value, groupSKPrefix):
			var v Group
			if err := attributevalue.UnmarshalMap(item, &v); err != nil {
				return err
			}
			c.Groups = append(c.Groups, v)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return c, nil
}

func (r *PollsRepositoryImpl) GetRecipient(ctx context.Context, callbackID, userID string) (*Recipient, error) {
	out, err := r.client.GetItem(ctx, &dynamodb.GetItemInput{
		TableName:      r.table(),
		Key:            key(PollPartitionKey(callbackID), RecipientSortKey(userID)),
		ConsistentRead: aws.Bool(true),
	})
	if err != nil || out.Item == nil {
		return nil, err
	}
	var v Recipient
	if err := attributevalue.UnmarshalMap(out.Item, &v); err != nil {
		return nil, err
	}
	return &v, nil
}

func (r *PollsRepositoryImpl) MarkRecipientSent(ctx context.Context, callbackID, userID, messageTS string, now time.Time) error {
	av, err := attributevalue.MarshalMap(Recipient{
		PK:        PollPartitionKey(callbackID),
		SK:        RecipientSortKey(userID),
		UserID:    userID,
		SentAt:    At(now),
		MessageTS: messageTS,
	})
	if err != nil {
		return err
	}
	_, err = r.client.PutItem(ctx, &dynamodb.PutItemInput{TableName: r.table(), Item: av})
	return err
}

func (r *PollsRepositoryImpl) SaveGroups(ctx context.Context, callbackID string, groups []polls.Group) ([]Group, error) {
	if len(groups) > MaxGroupsPerPoll {
		return nil, fmt.Errorf("poll %s would have %d groups; at most %d are supported", callbackID, len(groups), MaxGroupsPerPoll)
	}

	stored := make([]Group, 0, len(groups))
	items := make([]types.TransactWriteItem, 0, len(groups)+1)
	indexByKey := map[string]int{}
	for _, g := range groups {
		group := Group{
			PK:          PollPartitionKey(callbackID),
			SK:          GroupSortKey(g.ResponseKey, indexByKey[g.ResponseKey]),
			CallbackID:  callbackID,
			ResponseKey: g.ResponseKey,
			UserIDs:     g.UserIDs,
		}
		indexByKey[g.ResponseKey]++
		av, err := attributevalue.MarshalMap(group)
		if err != nil {
			return nil, err
		}
		stored = append(stored, group)
		items = append(items, types.TransactWriteItem{Put: &types.Put{
			TableName:           r.table(),
			Item:                av,
			ConditionExpression: aws.String("attribute_not_exists(pk)"),
		}})
	}
	// Recording group_count on the poll in the same transaction makes "groups formed" an
	// all-or-nothing fact: a retry either sees every group or none of them.
	items = append(items, types.TransactWriteItem{Update: &types.Update{
		TableName:                r.table(),
		Key:                      key(PollPartitionKey(callbackID), PollSortKey),
		UpdateExpression:         aws.String("SET group_count = :count"),
		ConditionExpression:      aws.String("#state = :closed AND attribute_not_exists(group_count)"),
		ExpressionAttributeNames: map[string]string{"#state": "state"},
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":count":  n(int64(len(groups))),
			":closed": s(StateClosed),
		},
	}})

	_, err := r.client.TransactWriteItems(ctx, &dynamodb.TransactWriteItemsInput{TransactItems: items})
	if cancellationCodes(err) != nil {
		return nil, ErrInvalidTransition
	}
	if err != nil {
		return nil, err
	}
	return stored, nil
}

func (r *PollsRepositoryImpl) GetGroup(ctx context.Context, callbackID, groupSK string) (*Group, error) {
	out, err := r.client.GetItem(ctx, &dynamodb.GetItemInput{
		TableName:      r.table(),
		Key:            key(PollPartitionKey(callbackID), groupSK),
		ConsistentRead: aws.Bool(true),
	})
	if err != nil || out.Item == nil {
		return nil, err
	}
	var g Group
	if err := attributevalue.UnmarshalMap(out.Item, &g); err != nil {
		return nil, err
	}
	return &g, nil
}

func (r *PollsRepositoryImpl) MarkGroupNotified(ctx context.Context, callbackID, groupSK string, now time.Time) error {
	_, err := r.client.UpdateItem(ctx, &dynamodb.UpdateItemInput{
		TableName:           r.table(),
		Key:                 key(PollPartitionKey(callbackID), groupSK),
		UpdateExpression:    aws.String("SET notified_at = :now"),
		ConditionExpression: aws.String("attribute_exists(pk)"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":now": ts(now),
		},
	})
	return err
}
