package repositories

import (
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
)

// TimestampLayout is how every timestamp is stored: ISO 8601, always UTC, always millisecond
// precision. The fixed width matters: these strings are compared and sorted as text (the
// ACTIVE_POLL cutoff condition), which only matches time order when
// every value has the same shape. time.RFC3339Nano trims trailing zeros, so it can't be used.
const TimestampLayout = "2006-01-02T15:04:05.000Z"

// Timestamp is a time.Time stored as a TimestampLayout string. Optional timestamps are
// *Timestamp with omitempty, so an unset one isn't written at all (attributevalue writes a
// custom type's zero value as NULL even with omitempty).
type Timestamp struct{ time.Time }

// At returns t truncated to the stored (millisecond) precision, so a value read back equals
// the value written.
func At(t time.Time) Timestamp { return Timestamp{t.UTC().Truncate(time.Millisecond)} }

// String formats the timestamp as stored, or "" when unset.
func (t Timestamp) String() string {
	if t.IsZero() {
		return ""
	}
	return t.UTC().Format(TimestampLayout)
}

func (t Timestamp) MarshalDynamoDBAttributeValue() (types.AttributeValue, error) {
	if t.IsZero() {
		return &types.AttributeValueMemberNULL{Value: true}, nil
	}
	return &types.AttributeValueMemberS{Value: t.String()}, nil
}

func (t *Timestamp) UnmarshalDynamoDBAttributeValue(av types.AttributeValue) error {
	switch v := av.(type) {
	case *types.AttributeValueMemberNULL:
		*t = Timestamp{}
		return nil
	case *types.AttributeValueMemberS:
		parsed, err := time.Parse(TimestampLayout, v.Value)
		if err != nil {
			return fmt.Errorf("timestamp %q: %w", v.Value, err)
		}
		*t = Timestamp{parsed}
		return nil
	default:
		return fmt.Errorf("timestamp: unexpected attribute type %T", av)
	}
}

// AtPtr is At for optional (*Timestamp) fields.
func AtPtr(t time.Time) *Timestamp { v := At(t); return &v }

// ts is the attribute value for a timestamp in an expression.
func ts(t time.Time) types.AttributeValue { return s(At(t).String()) }
