package workflows

import (
	"context"
	"errors"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/sfn"
	sfntypes "github.com/aws/aws-sdk-go-v2/service/sfn/types"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/repositories/memory"
	"github.com/qsweber/lunch-buddies/internal/slack"
	"github.com/qsweber/lunch-buddies/internal/slack/slacktest"
)

var now = time.Date(2026, 11, 3, 18, 0, 0, 0, time.UTC)

type harness struct {
	Deps
	store *memory.Store
	slack *slacktest.Fake
}

func newHarness(t *testing.T) *harness {
	t.Helper()
	store := memory.New()
	fake := slacktest.New()
	_ = store.PutTeam(context.Background(), repositories.Team{TeamID: "T1", BotAccessToken: "xoxb"})
	return &harness{
		Deps:  Deps{Repositories: store.Repositories(), Slack: fake, Now: func() time.Time { return now }, Rand: seededForTest(1)},
		store: store,
		slack: fake,
	}
}

func (h *harness) request(t *testing.T, id, channel string) {
	t.Helper()
	err := h.store.CreateRequestedPoll(context.Background(), repositories.Poll{
		CallbackID: id, TeamID: "T1", ChannelID: channel, CreatedByUserID: "U1",
		CreatedAt: now.UnixMilli(), Choices: polls.DefaultChoices(), GroupSize: 2,
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestEndToEndPollLifecycle(t *testing.T) {
	ctx := context.Background()
	h := newHarness(t)
	h.slack.Members["C1"] = []string{"U1", "U2", "U3", "U4"}
	h.request(t, "cb", "C1")

	prep, err := h.PreparePoll(ctx, PollInput{CallbackID: "cb"})
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(prep.UserIDs, []string{"U1", "U2", "U3", "U4"}) {
		t.Fatalf("users = %v", prep.UserIDs)
	}
	if h.store.Polls["cb"].State != repositories.StateOpen {
		t.Fatal("poll should be OPEN")
	}

	for _, u := range prep.UserIDs {
		if err := h.PollUser(ctx, PollUserInput{CallbackID: "cb", UserID: u}); err != nil {
			t.Fatal(err)
		}
	}
	// Retrying a user must not DM them again.
	_ = h.PollUser(ctx, PollUserInput{CallbackID: "cb", UserID: "U2"})
	if got := h.slack.PostedTo("U2"); len(got) != 1 || got[0] != polls.MsgPollQuestion {
		t.Errorf("U2 DMs = %v", got)
	}

	for _, u := range []string{"U1", "U2", "U3"} {
		_ = h.store.RecordResponse(ctx, repositories.PollResponse{CallbackID: "cb", UserID: u, Response: "yes_1200"})
	}
	_ = h.store.RecordResponse(ctx, repositories.PollResponse{CallbackID: "cb", UserID: "U4", Response: "no"})
	active, _ := h.store.GetActivePoll(ctx, "T1", "C1")
	if err := h.store.ClosePoll(ctx, *active, "U1", now); err != nil {
		t.Fatal(err)
	}

	formed, err := h.FormGroups(ctx, PollInput{CallbackID: "cb"})
	if err != nil {
		t.Fatal(err)
	}
	// Same as Python: 3 "yes" at group size 2 (min size 1) gives groups of 2 and 1.
	if len(formed.GroupSKs) != 2 {
		t.Fatalf("groups = %v", formed.GroupSKs)
	}
	again, _ := h.FormGroups(ctx, PollInput{CallbackID: "cb"})
	if !reflect.DeepEqual(again, formed) {
		t.Errorf("retry re-formed groups: %v vs %v", again, formed)
	}

	for _, sk := range formed.GroupSKs {
		if err := h.NotifyGroup(ctx, NotifyGroupInput{CallbackID: "cb", GroupSK: sk}); err != nil {
			t.Fatal(err)
		}
		_ = h.NotifyGroup(ctx, NotifyGroupInput{CallbackID: "cb", GroupSK: sk})
	}
	posted := h.slack.PostedTo("C1")
	if len(posted) != 4 {
		t.Fatalf("channel posts = %v (want group message + threaded picker per group, once each)", posted)
	}
	if !strings.HasPrefix(posted[0], "Hey <@") || !strings.HasSuffix(posted[0], "You all should meet somewhere at `12:00`.") {
		t.Errorf("group message = %q", posted[0])
	}
	if h.slack.Posted[len(h.slack.Posted)-1].ThreadTS == "" {
		t.Error("location picker should be threaded")
	}
}

func TestPreparePollRejectsSecondPollInChannel(t *testing.T) {
	ctx := context.Background()
	h := newHarness(t)
	h.slack.Members["C1"] = []string{"U1"}
	h.request(t, "first", "C1")
	h.request(t, "second", "C1")

	if _, err := h.PreparePoll(ctx, PollInput{CallbackID: "first"}); err != nil {
		t.Fatal(err)
	}
	out, err := h.PreparePoll(ctx, PollInput{CallbackID: "second"})
	if err != nil {
		t.Fatal(err)
	}
	if len(out.UserIDs) != 0 || h.store.Polls["second"].State != repositories.StateRejected {
		t.Errorf("second poll = %+v, users %v", h.store.Polls["second"], out.UserIDs)
	}
	if got := h.slack.PostedTo("U1"); len(got) != 1 || got[0] != polls.MsgActivePollExists {
		t.Errorf("creator DMs = %v", got)
	}
	// Re-running the rejected poll is a no-op.
	if out, _ := h.PreparePoll(ctx, PollInput{CallbackID: "second"}); len(out.UserIDs) != 0 || len(h.slack.PostedTo("U1")) != 1 {
		t.Error("re-run of a rejected poll should do nothing")
	}
}

func TestPreparePollSlashCommandChannelResolution(t *testing.T) {
	ctx := context.Background()

	h := newHarness(t)
	h.request(t, "cb", "")
	_, _ = h.PreparePoll(ctx, PollInput{CallbackID: "cb"})
	if h.store.Polls["cb"].RejectionReason != "default_channel_not_found" || h.slack.PostedTo("U1")[0] != polls.DefaultChannelNotFound {
		t.Errorf("poll = %+v", h.store.Polls["cb"])
	}

	h = newHarness(t)
	h.slack.Channels[polls.DefaultChannelName] = slack.Channel{ID: "CLB", Name: polls.DefaultChannelName}
	h.slack.Members["CLB"] = []string{"U7"}
	h.request(t, "cb", "")
	_, _ = h.PreparePoll(ctx, PollInput{CallbackID: "cb"})
	if h.store.Polls["cb"].RejectionReason != "user_not_in_default_channel" || !strings.Contains(h.slack.PostedTo("U1")[0], "<#CLB|lunch_buddies>") {
		t.Errorf("poll = %+v", h.store.Polls["cb"])
	}

	h = newHarness(t)
	h.slack.Channels[polls.DefaultChannelName] = slack.Channel{ID: "CLB", Name: polls.DefaultChannelName}
	h.slack.Members["CLB"] = []string{"U1", "U7"}
	h.request(t, "cb", "")
	out, _ := h.PreparePoll(ctx, PollInput{CallbackID: "cb"})
	if h.store.Polls["cb"].ChannelID != "CLB" || len(out.UserIDs) != 2 {
		t.Errorf("poll = %+v users = %v", h.store.Polls["cb"], out.UserIDs)
	}
}

func TestFormGroupsWithNoResponsesDMsCloser(t *testing.T) {
	ctx := context.Background()
	h := newHarness(t)
	h.slack.Members["C1"] = []string{"U1"}
	h.request(t, "cb", "C1")
	_, _ = h.PreparePoll(ctx, PollInput{CallbackID: "cb"})
	active, _ := h.store.GetActivePoll(ctx, "T1", "C1")
	_ = h.store.ClosePoll(ctx, *active, "U9", now)

	out, err := h.FormGroups(ctx, PollInput{CallbackID: "cb"})
	if err != nil || len(out.GroupSKs) != 0 {
		t.Fatalf("out = %+v, err = %v", out, err)
	}
	_, _ = h.FormGroups(ctx, PollInput{CallbackID: "cb"})
	if got := h.slack.PostedTo("U9"); len(got) != 1 || got[0] != polls.MsgNoPollResponses {
		t.Errorf("closer DMs = %v (want exactly one)", got)
	}
}

func TestPollUserPropagatesRateLimit(t *testing.T) {
	ctx := context.Background()
	h := newHarness(t)
	h.slack.Members["C1"] = []string{"U1"}
	h.request(t, "cb", "C1")
	_, _ = h.PreparePoll(ctx, PollInput{CallbackID: "cb"})
	h.slack.PostErrors = []error{&slack.RateLimitedError{Method: "chat.postMessage", RetryAfter: time.Second}}

	err := h.PollUser(ctx, PollUserInput{CallbackID: "cb", UserID: "U1"})
	var rl *slack.RateLimitedError
	if !errors.As(err, &rl) {
		t.Fatalf("err = %v, want RateLimitedError so the Step Functions Retry matches it", err)
	}
	if r, _ := h.store.GetRecipient(ctx, "cb", "U1"); r != nil {
		t.Error("recipient must not be marked sent on failure")
	}
}

// Stream records.

func image(kv map[string]string) map[string]events.DynamoDBAttributeValue {
	out := map[string]events.DynamoDBAttributeValue{}
	for k, v := range kv {
		out[k] = events.NewStringAttribute(v)
	}
	return out
}

func pollRecord(name, oldState, newState string) events.DynamoDBEventRecord {
	r := events.DynamoDBEventRecord{EventName: name}
	r.Change.SequenceNumber = "seq-" + newState
	r.Change.NewImage = image(map[string]string{"pk": "POLL#cb", "sk": "POLL", "callback_id": "cb", "state": newState})
	if oldState != "" {
		r.Change.OldImage = image(map[string]string{"state": oldState})
	}
	return r
}

func TestClassify(t *testing.T) {
	cases := []struct {
		record events.DynamoDBEventRecord
		want   Transition
	}{
		{pollRecord("INSERT", "", repositories.StateRequested), TransitionPollRequested},
		{pollRecord("MODIFY", repositories.StateOpen, repositories.StateClosed), TransitionPollClosed},
		{pollRecord("MODIFY", repositories.StateRequested, repositories.StateOpen), TransitionNone},
		{pollRecord("MODIFY", repositories.StateClosed, repositories.StateClosed), TransitionNone},
		{pollRecord("MODIFY", repositories.StateClosed, repositories.StateComplete), TransitionNone},
		// Migrated rows arrive as INSERTs in non-REQUESTED states and must not trigger anything.
		{pollRecord("INSERT", "", repositories.StateOpen), TransitionNone},
		{pollRecord("INSERT", "", repositories.StateComplete), TransitionNone},
		{events.DynamoDBEventRecord{EventName: "INSERT", Change: events.DynamoDBStreamRecord{
			NewImage: image(map[string]string{"pk": "POLL#cb", "sk": "RESPONSE#U1", "state": repositories.StateRequested}),
		}}, TransitionNone},
	}
	for i, c := range cases {
		if got, _ := Classify(c.record); got != c.want {
			t.Errorf("case %d: Classify = %v, want %v", i, got, c.want)
		}
	}
}

type fakeSFN struct {
	inputs []sfn.StartExecutionInput
	errs   []error
}

func (f *fakeSFN) StartExecution(_ context.Context, p *sfn.StartExecutionInput, _ ...func(*sfn.Options)) (*sfn.StartExecutionOutput, error) {
	f.inputs = append(f.inputs, *p)
	if len(f.errs) > 0 {
		err := f.errs[0]
		f.errs = f.errs[1:]
		return nil, err
	}
	return &sfn.StartExecutionOutput{}, nil
}

func TestRouterStartsNamedExecutionsAndReportsFailures(t *testing.T) {
	f := &fakeSFN{errs: []error{nil, &sfntypes.ExecutionAlreadyExists{}, errors.New("throttled")}}
	r := Router{SFN: f, StartPollStateMachine: "arn:start", ClosePollStateMachine: "arn:close"}
	resp, err := r.Handle(context.Background(), events.DynamoDBEvent{Records: []events.DynamoDBEventRecord{
		pollRecord("INSERT", "", repositories.StateRequested),
		pollRecord("INSERT", "", repositories.StateRequested), // duplicate delivery
		pollRecord("MODIFY", repositories.StateOpen, repositories.StateClosed),
		pollRecord("MODIFY", repositories.StateRequested, repositories.StateOpen),
	}})
	if err != nil {
		t.Fatal(err)
	}
	if len(f.inputs) != 3 {
		t.Fatalf("StartExecution calls = %d", len(f.inputs))
	}
	if aws.ToString(f.inputs[0].Name) != "start-cb" || aws.ToString(f.inputs[0].StateMachineArn) != "arn:start" || aws.ToString(f.inputs[0].Input) != `{"callback_id":"cb"}` {
		t.Errorf("first = %+v", f.inputs[0])
	}
	if aws.ToString(f.inputs[2].Name) != "close-cb" || aws.ToString(f.inputs[2].StateMachineArn) != "arn:close" {
		t.Errorf("third = %+v", f.inputs[2])
	}
	if len(resp.BatchItemFailures) != 1 || resp.BatchItemFailures[0].ItemIdentifier != "seq-CLOSED" {
		t.Errorf("failures = %+v (only the throttled record should be retried)", resp.BatchItemFailures)
	}
}

func TestWorkerDispatchesByTask(t *testing.T) {
	ctx := context.Background()
	h := newHarness(t)
	h.slack.Members["C1"] = []string{"U1", "U2"}
	h.request(t, "cb", "C1")

	out, err := h.Handle(ctx, []byte(`{"task":"prepare-poll","callback_id":"cb"}`))
	if err != nil {
		t.Fatal(err)
	}
	if prep := out.(PrepareOutput); len(prep.UserIDs) != 2 {
		t.Fatalf("prepare output = %+v", out)
	}
	if _, err := h.Handle(ctx, []byte(`{"task":"poll-user","callback_id":"cb","user_id":"U2"}`)); err != nil {
		t.Fatal(err)
	}
	if got := h.slack.PostedTo("U2"); len(got) != 1 {
		t.Errorf("U2 DMs = %v", got)
	}

	if _, err := h.Handle(ctx, []byte(`{"task":"bogus"}`)); err == nil {
		t.Error("unknown task should fail")
	}

	h.slack.PostErrors = []error{&slack.RateLimitedError{Method: "chat.postMessage"}}
	_, err = h.Handle(ctx, []byte(`{"task":"poll-user","callback_id":"cb","user_id":"U1"}`))
	if _, ok := err.(*slack.RateLimitedError); !ok {
		t.Errorf("err = %T, want an unwrapped *slack.RateLimitedError so Step Functions Retry matches it", err)
	}
}
