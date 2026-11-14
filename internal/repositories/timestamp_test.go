package repositories

import (
	"sort"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
)

func TestTimestampRoundTripAndOmitEmpty(t *testing.T) {
	type item struct {
		Created Timestamp  `dynamodbav:"created_at"`
		Closed  *Timestamp `dynamodbav:"closed_at,omitempty"`
	}
	when := time.Date(2026, 11, 14, 18, 3, 12, 123456789, time.FixedZone("PST", -8*3600))
	av, err := attributevalue.MarshalMap(item{Created: At(when)})
	if err != nil {
		t.Fatal(err)
	}
	if got := av["created_at"].(*types.AttributeValueMemberS).Value; got != "2026-11-15T02:03:12.123Z" {
		t.Errorf("stored as %q", got)
	}
	if _, ok := av["closed_at"]; ok {
		t.Errorf("an unset omitempty timestamp must not be written, got %#v", av["closed_at"])
	}

	var back item
	if err := attributevalue.UnmarshalMap(av, &back); err != nil {
		t.Fatal(err)
	}
	if !back.Created.Equal(At(when).Time) || back.Closed != nil {
		t.Errorf("round trip = %+v", back)
	}
}

func TestTimestampStringsSortInTimeOrder(t *testing.T) {
	base := time.Date(2026, 1, 1, 0, 0, 12, 0, time.UTC)
	times := []time.Time{base.Add(100 * time.Millisecond), base, base.Add(time.Second), base.Add(10 * time.Millisecond)}
	var strs []string
	for _, tm := range times {
		strs = append(strs, At(tm).String())
	}
	sort.Strings(strs)
	want := []string{"2026-01-01T00:00:12.000Z", "2026-01-01T00:00:12.010Z", "2026-01-01T00:00:12.100Z", "2026-01-01T00:00:13.000Z"}
	for i := range want {
		if strs[i] != want[i] {
			t.Fatalf("sorted = %v, want %v", strs, want)
		}
	}
}
