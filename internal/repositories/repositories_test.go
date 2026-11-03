package repositories

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"

	"github.com/qsweber/lunch-buddies/internal/polls"
)

const testTable = "test-records"

// fakeDynamoDB records the inputs it receives and returns the configured outputs.
type fakeDynamoDB struct {
	putInput      *dynamodb.PutItemInput
	putErr        error
	getOutput     *dynamodb.GetItemOutput
	getInput      *dynamodb.GetItemInput
	updateInput   *dynamodb.UpdateItemInput
	updateErr     error
	queryInputs   []dynamodb.QueryInput
	queryOutputs  []*dynamodb.QueryOutput
	transactInput *dynamodb.TransactWriteItemsInput
	transactErr   error
}

func (f *fakeDynamoDB) PutItem(_ context.Context, p *dynamodb.PutItemInput, _ ...func(*dynamodb.Options)) (*dynamodb.PutItemOutput, error) {
	f.putInput = p
	return &dynamodb.PutItemOutput{}, f.putErr
}

func (f *fakeDynamoDB) GetItem(_ context.Context, p *dynamodb.GetItemInput, _ ...func(*dynamodb.Options)) (*dynamodb.GetItemOutput, error) {
	f.getInput = p
	if f.getOutput == nil {
		return &dynamodb.GetItemOutput{}, nil
	}
	return f.getOutput, nil
}

func (f *fakeDynamoDB) UpdateItem(_ context.Context, p *dynamodb.UpdateItemInput, _ ...func(*dynamodb.Options)) (*dynamodb.UpdateItemOutput, error) {
	f.updateInput = p
	return &dynamodb.UpdateItemOutput{}, f.updateErr
}

func (f *fakeDynamoDB) Query(_ context.Context, p *dynamodb.QueryInput, _ ...func(*dynamodb.Options)) (*dynamodb.QueryOutput, error) {
	f.queryInputs = append(f.queryInputs, *p)
	out := f.queryOutputs[0]
	f.queryOutputs = f.queryOutputs[1:]
	return out, nil
}

func (f *fakeDynamoDB) TransactWriteItems(_ context.Context, p *dynamodb.TransactWriteItemsInput, _ ...func(*dynamodb.Options)) (*dynamodb.TransactWriteItemsOutput, error) {
	f.transactInput = p
	return &dynamodb.TransactWriteItemsOutput{}, f.transactErr
}

func (f *fakeDynamoDB) BatchWriteItem(context.Context, *dynamodb.BatchWriteItemInput, ...func(*dynamodb.Options)) (*dynamodb.BatchWriteItemOutput, error) {
	return &dynamodb.BatchWriteItemOutput{}, nil
}

func canceled(codes ...string) error {
	reasons := make([]types.CancellationReason, len(codes))
	for i, c := range codes {
		reasons[i] = types.CancellationReason{Code: aws.String(c)}
	}
	return &types.TransactionCanceledException{CancellationReasons: reasons}
}

func str(t *testing.T, item map[string]types.AttributeValue, name string) string {
	t.Helper()
	v, ok := item[name].(*types.AttributeValueMemberS)
	if !ok {
		t.Fatalf("attribute %q is %T, want string", name, item[name])
	}
	return v.Value
}

func TestCreateRequestedPollKeysAndCondition(t *testing.T) {
	db := &fakeDynamoDB{}
	repo := NewPollsRepository(testTable, db)
	err := repo.CreateRequestedPoll(context.Background(), Poll{
		CallbackID: "cb1", TeamID: "T1", CreatedAt: 1700000000000, Choices: polls.DefaultChoices(), GroupSize: 6,
	})
	if err != nil {
		t.Fatal(err)
	}
	item := db.putInput.Item
	checks := map[string]string{
		"pk": "POLL#cb1", "sk": "POLL", "gsi1pk": "TEAM#T1", "gsi1sk": "POLL#1700000000000", "state": StateRequested,
	}
	for k, want := range checks {
		if got := str(t, item, k); got != want {
			t.Errorf("%s = %q, want %q", k, got, want)
		}
	}
	if aws.ToString(db.putInput.ConditionExpression) != "attribute_not_exists(pk)" {
		t.Errorf("condition = %q", aws.ToString(db.putInput.ConditionExpression))
	}
	if _, ok := item["channel_id"]; ok {
		t.Error("empty channel_id should be omitted")
	}
}

func TestOpenPollMapsCancellationReasons(t *testing.T) {
	poll := Poll{CallbackID: "cb1", TeamID: "T1", CreatedAt: 1}
	now := time.UnixMilli(ActivePollTTL.Milliseconds() + 5000)

	cases := []struct {
		err  error
		want error
	}{
		{nil, nil},
		{canceled(conditionalCheckFailed, "None"), ErrInvalidTransition},
		{canceled("None", conditionalCheckFailed), ErrActivePollExists},
	}
	for _, c := range cases {
		db := &fakeDynamoDB{transactErr: c.err}
		err := NewPollsRepository(testTable, db).OpenPoll(context.Background(), poll, "C1", now)
		if !errors.Is(err, c.want) && err != c.want {
			t.Errorf("OpenPoll with %v = %v, want %v", c.err, err, c.want)
		}
		put := db.transactInput.TransactItems[1].Put
		if got := str(t, put.Item, "sk"); got != "ACTIVE_POLL#C1" {
			t.Errorf("pointer sk = %q", got)
		}
		cutoff := put.ExpressionAttributeValues[":cutoff"].(*types.AttributeValueMemberN).Value
		if cutoff != "5000" {
			t.Errorf("cutoff = %s, want 5000", cutoff)
		}
	}
}

func TestClosePollAndRecordResponseMapToErrPollNotOpen(t *testing.T) {
	db := &fakeDynamoDB{transactErr: canceled(conditionalCheckFailed, "None")}
	repo := NewPollsRepository(testTable, db)
	if err := repo.ClosePoll(context.Background(), ActivePoll{TeamID: "T", ChannelID: "C", CallbackID: "cb"}, "U", time.Now()); err != ErrPollNotOpen {
		t.Errorf("ClosePoll = %v", err)
	}
	if err := repo.RecordResponse(context.Background(), PollResponse{CallbackID: "cb", UserID: "U", Response: "no"}); err != ErrPollNotOpen {
		t.Errorf("RecordResponse = %v", err)
	}
	if got := str(t, db.transactInput.TransactItems[1].Put.Item, "sk"); got != "RESPONSE#U" {
		t.Errorf("response sk = %q", got)
	}
}

func TestSaveGroupsAssignsPerChoiceIndexes(t *testing.T) {
	db := &fakeDynamoDB{}
	stored, err := NewPollsRepository(testTable, db).SaveGroups(context.Background(), "cb", []polls.Group{
		{ResponseKey: "yes_1200", UserIDs: []string{"a"}},
		{ResponseKey: "yes_1200", UserIDs: []string{"b"}},
		{ResponseKey: "yes_1300", UserIDs: []string{"c"}},
	})
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"GROUP#yes_1200#000", "GROUP#yes_1200#001", "GROUP#yes_1300#000"}
	for i, g := range stored {
		if g.SK != want[i] {
			t.Errorf("stored[%d].SK = %q, want %q", i, g.SK, want[i])
		}
	}
	if len(db.transactInput.TransactItems) != 4 || db.transactInput.TransactItems[3].Update == nil {
		t.Errorf("expected 3 puts + poll update, got %+v", db.transactInput.TransactItems)
	}
}

func TestGetPollCollectionSplitsItemsBySortKey(t *testing.T) {
	mk := func(v any) map[string]types.AttributeValue {
		av, err := attributevalue.MarshalMap(v)
		if err != nil {
			t.Fatal(err)
		}
		return av
	}
	db := &fakeDynamoDB{queryOutputs: []*dynamodb.QueryOutput{
		{
			Items: []map[string]types.AttributeValue{
				mk(Poll{CallbackID: "cb", State: StateOpen}.WithKeys()),
				mk(PollResponse{CallbackID: "cb", UserID: "U1", Response: "yes_1200"}.WithKeys()),
			},
			LastEvaluatedKey: key("POLL#cb", "RESPONSE#U1"),
		},
		{
			Items: []map[string]types.AttributeValue{
				mk(Group{PK: "POLL#cb", SK: GroupSortKey("yes_1200", 0), UserIDs: []string{"U1"}}),
				mk(Recipient{PK: "POLL#cb", SK: RecipientSortKey("U1"), UserID: "U1"}),
			},
		},
	}}
	c, err := NewPollsRepository(testTable, db).GetPollCollection(context.Background(), "cb")
	if err != nil {
		t.Fatal(err)
	}
	if c.Poll == nil || len(c.Responses) != 1 || len(c.Groups) != 1 || len(c.Recipients) != 1 {
		t.Errorf("collection = %+v", c)
	}
	if len(db.queryInputs) != 2 || db.queryInputs[1].ExclusiveStartKey == nil {
		t.Error("expected a second paged query")
	}
	if !aws.ToBool(db.queryInputs[0].ConsistentRead) {
		t.Error("collection reads must be strongly consistent")
	}
}

func TestTeamsRepository(t *testing.T) {
	db := &fakeDynamoDB{}
	repo := NewTeamsRepository(testTable, db)
	if err := repo.PutTeam(context.Background(), Team{TeamID: "T1", BotAccessToken: "xoxb-123"}); err != nil {
		t.Fatal(err)
	}
	if str(t, db.putInput.Item, "pk") != "TEAM#T1" || str(t, db.putInput.Item, "gsi1pk") != AllTeamsGSI1PK {
		t.Errorf("team keys = %+v", db.putInput.Item)
	}
	if got := str(t, db.putInput.Item, "bot_access_token"); got != "xoxb-123" {
		t.Errorf("bot_access_token = %q", got)
	}

	db.getOutput = &dynamodb.GetItemOutput{Item: db.putInput.Item}
	got, err := repo.GetTeam(context.Background(), "T1")
	if err != nil || got.BotAccessToken != "xoxb-123" {
		t.Errorf("GetTeam = %+v, %v", got, err)
	}
	if err := repo.PutTeam(context.Background(), Team{TeamID: "T1"}); err == nil {
		t.Error("PutTeam without a token should fail")
	}
	db.getOutput = nil
	team, err := repo.GetTeam(context.Background(), "missing")
	if err != nil || team != nil {
		t.Errorf("GetTeam(missing) = %v, %v", team, err)
	}
}
