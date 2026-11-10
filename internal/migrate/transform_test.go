package migrate

import (
	"context"
	"reflect"
	"testing"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
)

func TestChoicesAllLegacyFormats(t *testing.T) {
	want := []polls.Choice{
		{Key: "yes_1145", IsYes: true, Time: "11:45", DisplayText: "Yes (11:45)"},
		{Key: "no", IsYes: false, Time: "", DisplayText: "No"},
	}
	for _, raw := range []string{
		`{"no": "No", "yes_1145": "Yes (11:45)"}`,
		`[["yes_1145", "Yes (11:45)"], ["no", "No"]]`,
		`[{"key": "yes_1145", "is_yes": true, "time": "11:45", "display_text": "Yes (11:45)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]`,
	} {
		got, err := Choices(raw)
		if err != nil || !reflect.DeepEqual(got, want) {
			t.Errorf("Choices(%s) = %+v, %v", raw, got, err)
		}
	}
}

func TestPollStateMappingAndTimestamps(t *testing.T) {
	row := Row{
		"team_id": "T1", "callback_id": "cb", "created_at": "1700000000.123456",
		"channel_id": "C1", "created_by_user_id": "U1", "state": "CREATED",
		"choices": `[["yes_1200", "Yes (12:00)"]]`, "group_size": "4",
	}
	p, err := Poll(row, 0)
	if err != nil {
		t.Fatal(err)
	}
	if p.State != repositories.StateOpen || p.CreatedAt != 1700000000123 || p.GroupSize != 4 || p.GroupCount != nil {
		t.Errorf("open poll = %+v", p)
	}

	row["state"] = "CLOSED"
	p, _ = Poll(row, 3)
	if p.State != repositories.StateComplete || p.GroupCount == nil || *p.GroupCount != 3 {
		t.Errorf("closed poll = %+v", p)
	}
}

func TestGroupKeyIsStableAndOrderIndependent(t *testing.T) {
	a, _ := Group(Row{"callback_id": "cb", "response_key": "yes_1200", "user_ids": `["U2","U1"]`})
	b, _ := Group(Row{"callback_id": "cb", "response_key": "yes_1200", "user_ids": `["U1","U2"]`})
	if a.SK != b.SK || a.PK != "POLL#cb" || a.NotifiedAt == 0 {
		t.Errorf("a = %+v, b = %+v", a, b)
	}
}

func TestActivePointersKeepsNewestOpenPollPerChannel(t *testing.T) {
	got := ActivePointers([]repositories.Poll{
		{CallbackID: "old", TeamID: "T", ChannelID: "C", CreatedAt: 1, State: repositories.StateOpen},
		{CallbackID: "new", TeamID: "T", ChannelID: "C", CreatedAt: 2, State: repositories.StateOpen},
		{CallbackID: "done", TeamID: "T", ChannelID: "D", CreatedAt: 3, State: repositories.StateComplete},
		{CallbackID: "nochan", TeamID: "T", CreatedAt: 4, State: repositories.StateOpen},
	})
	if len(got) != 1 || got[0].CallbackID != "new" || got[0].SK != "ACTIVE_POLL#C" {
		t.Errorf("pointers = %+v", got)
	}
}

func TestTeamBooleans(t *testing.T) {
	team, err := Team(Row{"team_id": "T", "bot_access_token": "xoxb", "created_at": "1600000000", "feature_notify_in_channel": "1"})
	if err != nil || !team.FeatureNotifyInChannel || team.CreatedAt != 1600000000000 {
		t.Errorf("team = %+v, %v", team, err)
	}
}

type fakeWriter struct {
	updateErr error
	deleteErr error
	updates   []dynamodb.UpdateItemInput
	deletes   []dynamodb.DeleteItemInput
}

func (f *fakeWriter) UpdateItem(_ context.Context, p *dynamodb.UpdateItemInput, _ ...func(*dynamodb.Options)) (*dynamodb.UpdateItemOutput, error) {
	f.updates = append(f.updates, *p)
	return &dynamodb.UpdateItemOutput{}, f.updateErr
}

func (f *fakeWriter) DeleteItem(_ context.Context, p *dynamodb.DeleteItemInput, _ ...func(*dynamodb.Options)) (*dynamodb.DeleteItemOutput, error) {
	f.deletes = append(f.deletes, *p)
	return &dynamodb.DeleteItemOutput{}, f.deleteErr
}

func TestCompleteIfOpen(t *testing.T) {
	two := 2
	poll := repositories.Poll{CallbackID: "cb", TeamID: "T", ChannelID: "C", State: repositories.StateComplete, GroupCount: &two}

	f := &fakeWriter{deleteErr: &types.ConditionalCheckFailedException{}}
	done, err := CompleteIfOpen(context.Background(), f, "tbl", poll)
	if err != nil || !done {
		t.Fatalf("done = %v, err = %v (a pointer now owned by another poll is fine)", done, err)
	}
	u := f.updates[0]
	if aws.ToString(u.ConditionExpression) != "#state = :open" || u.ExpressionAttributeValues[":complete"].(*types.AttributeValueMemberS).Value != repositories.StateComplete {
		t.Errorf("update = %+v", u)
	}
	if sk := f.deletes[0].Key["sk"].(*types.AttributeValueMemberS).Value; sk != "ACTIVE_POLL#C" {
		t.Errorf("deleted sk = %s", sk)
	}

	f = &fakeWriter{updateErr: &types.ConditionalCheckFailedException{}}
	done, err = CompleteIfOpen(context.Background(), f, "tbl", poll)
	if err != nil || done || len(f.deletes) != 0 {
		t.Errorf("a poll the new system moved on must be left alone: done=%v err=%v deletes=%d", done, err, len(f.deletes))
	}
}
