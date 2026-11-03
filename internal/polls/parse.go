// Package polls holds the pure domain logic for Lunch Buddies polls: parsing the poll
// options a user types, grouping respondents, and building the Slack messages. It does no
// I/O, so everything here is deterministic given its inputs.
package polls

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// DefaultGroupSize is used when the poll text doesn't specify "size=N".
const DefaultGroupSize = 6

// MaxGroupSize is the upper bound used when redistributing a too-small final group.
const MaxGroupSize = 7

// Choice is one button on the poll.
type Choice struct {
	Key         string `dynamodbav:"key" json:"key"`
	IsYes       bool   `dynamodbav:"is_yes" json:"is_yes"`
	Time        string `dynamodbav:"time" json:"time"`
	DisplayText string `dynamodbav:"display_text" json:"display_text"`
}

// NoChoice is always appended as the last option.
var NoChoice = Choice{Key: "no", IsYes: false, Time: "", DisplayText: "No"}

// DefaultChoices are used when the poll text is empty.
func DefaultChoices() []Choice {
	return []Choice{
		{Key: "yes_1200", IsYes: true, Time: "12:00", DisplayText: "Yes (12:00)"},
		NoChoice,
	}
}

// InvalidOptionError is returned when an option can't be parsed into a time.
type InvalidOptionError struct{ Option string }

func (e *InvalidOptionError) Error() string {
	return fmt.Sprintf("Option could not be parsed into a time: %q", e.Option)
}

// InvalidSizeError is returned when size=N is out of range or not a number.
type InvalidSizeError struct{ Size string }

func (e *InvalidSizeError) Error() string {
	return fmt.Sprintf("Size must be between 2 and 6. Received: %q", e.Size)
}

var sizePattern = regexp.MustCompile(`(.*)size=(.+)`)

// ParseText turns the text after "create" (e.g. "1145, 1230 size=4") into the poll's
// choices and group size. An empty text yields the defaults.
func ParseText(text string) ([]Choice, int, error) {
	if text == "" {
		return DefaultChoices(), DefaultGroupSize, nil
	}

	text, groupSize, err := groupSizeFromText(text)
	if err != nil {
		return nil, 0, err
	}

	var choices []Choice
	for _, option := range strings.Split(text, ",") {
		choice, err := choiceFromRawOption(strings.TrimSpace(option))
		if err != nil {
			return nil, 0, err
		}
		choices = append(choices, choice)
	}
	choices = append(choices, NoChoice)

	return choices, groupSize, nil
}

func groupSizeFromText(text string) (string, int, error) {
	text = strings.TrimSpace(text)
	match := sizePattern.FindStringSubmatch(text)
	if match == nil {
		return text, DefaultGroupSize, nil
	}
	size, err := strconv.Atoi(match[2])
	if err != nil {
		return "", 0, &InvalidSizeError{Size: match[2]}
	}
	if size <= 1 || size > 6 {
		return "", 0, &InvalidSizeError{Size: strconv.Itoa(size)}
	}
	return match[1], size, nil
}

func choiceFromRawOption(option string) (Choice, error) {
	if _, err := strconv.Atoi(option); err != nil {
		return Choice{}, &InvalidOptionError{Option: option}
	}
	if len(option) < 3 {
		return Choice{}, &InvalidOptionError{Option: option}
	}
	hour, _ := strconv.Atoi(option[:len(option)-2])
	minute, _ := strconv.Atoi(option[len(option)-2:])
	if hour < 0 || hour > 23 || minute < 0 || minute > 59 {
		return Choice{}, &InvalidOptionError{Option: option}
	}
	t := fmt.Sprintf("%d:%02d", hour, minute)
	return Choice{
		Key:         "yes_" + option,
		IsYes:       true,
		Time:        t,
		DisplayText: fmt.Sprintf("Yes (%s)", t),
	}, nil
}

// FindChoice returns the choice with the given key, or nil.
func FindChoice(choices []Choice, key string) *Choice {
	for i := range choices {
		if choices[i].Key == key {
			return &choices[i]
		}
	}
	return nil
}
