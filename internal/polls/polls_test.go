package polls

import (
	"errors"
	"math/rand/v2"
	"reflect"
	"sort"
	"strings"
	"testing"
)

// Cases ported from tests/actions/test_create_poll.py.

func TestParseTextTwoOptions(t *testing.T) {
	want := []Choice{
		{Key: "yes_1145", IsYes: true, Time: "11:45", DisplayText: "Yes (11:45)"},
		{Key: "yes_1230", IsYes: true, Time: "12:30", DisplayText: "Yes (12:30)"},
		NoChoice,
	}
	for _, text := range []string{"1145, 1230", "1145,1230", "  1145,   1230 "} {
		got, size, err := ParseText(text)
		if err != nil {
			t.Fatalf("ParseText(%q) error: %v", text, err)
		}
		if !reflect.DeepEqual(got, want) {
			t.Errorf("ParseText(%q) = %+v, want %+v", text, got, want)
		}
		if size != DefaultGroupSize {
			t.Errorf("ParseText(%q) size = %d, want %d", text, size, DefaultGroupSize)
		}
	}
}

func TestParseTextGroupSize(t *testing.T) {
	cases := []struct {
		text string
		size int
		want []string
	}{
		{"1200", DefaultGroupSize, []string{"yes_1200", "no"}},
		{" 1200   ", DefaultGroupSize, []string{"yes_1200", "no"}},
		{" 1200   size=5", 5, []string{"yes_1200", "no"}},
		{" 1200   size=4", 4, []string{"yes_1200", "no"}},
		{"1145,1200 size=3", 3, []string{"yes_1145", "yes_1200", "no"}},
		{" 1145, 1200      size=5", 5, []string{"yes_1145", "yes_1200", "no"}},
	}
	for _, c := range cases {
		choices, size, err := ParseText(c.text)
		if err != nil {
			t.Fatalf("ParseText(%q) error: %v", c.text, err)
		}
		var keys []string
		for _, ch := range choices {
			keys = append(keys, ch.Key)
		}
		if !reflect.DeepEqual(keys, c.want) || size != c.size {
			t.Errorf("ParseText(%q) = %v size %d, want %v size %d", c.text, keys, size, c.want, c.size)
		}
	}
}

func TestParseTextDefaults(t *testing.T) {
	choices, size, err := ParseText("")
	if err != nil || size != DefaultGroupSize || !reflect.DeepEqual(choices, DefaultChoices()) {
		t.Errorf("ParseText(\"\") = %v, %d, %v", choices, size, err)
	}
}

func TestParseTextErrors(t *testing.T) {
	var optErr *InvalidOptionError
	var sizeErr *InvalidSizeError
	cases := []struct {
		text   string
		target any
	}{
		{"noon", &optErr},
		{"2500", &optErr},
		{"1275", &optErr},
		{"12", &optErr},
		{"1200 size=7", &sizeErr},
		{"1200 size=1", &sizeErr},
		{"1200 size=big", &sizeErr},
	}
	for _, c := range cases {
		_, _, err := ParseText(c.text)
		if err == nil || !errors.As(err, c.target) {
			t.Errorf("ParseText(%q) error = %v, want %T", c.text, err, c.target)
		}
	}
}

// Python's test_get_groups asserts exact members under random.seed(0); Go's RNG differs, so
// we assert the group-size shape (which is independent of the shuffle) and that every element
// lands in exactly one group.
func TestGetGroupsShapes(t *testing.T) {
	cases := []struct {
		n, size, minSize, maxSize int
		wantSizes                 []int
	}{
		{11, 5, 3, 7, []int{6, 5}},
		{14, 5, 3, 7, []int{5, 5, 4}},
		{1, 10, 8, 10, []int{1}},
		{2, 2, 2, 2, []int{2}},
		{10, 7, 5, 7, []int{5, 5}},
		{18, 12, 12, 15, []int{9, 9}},
		{70, 6, 5, 7, []int{7, 7, 7, 7, 6, 6, 6, 6, 6, 6, 6}},
		{7, 5, 4, 7, []int{7}},
		{5, 3, 3, 7, []int{5}},
	}
	for _, c := range cases {
		elements := make([]int, c.n)
		for i := range elements {
			elements[i] = i
		}
		groups := GetGroups(elements, c.size, c.minSize, c.maxSize, rand.New(rand.NewPCG(0, 0)))
		var sizes []int
		var all []int
		for _, g := range groups {
			sizes = append(sizes, len(g))
			all = append(all, g...)
		}
		if !reflect.DeepEqual(sizes, c.wantSizes) {
			t.Errorf("GetGroups(n=%d, %d, %d, %d) sizes = %v, want %v", c.n, c.size, c.minSize, c.maxSize, sizes, c.wantSizes)
		}
		sort.Ints(all)
		if !reflect.DeepEqual(all, elements) {
			t.Errorf("GetGroups(n=%d) lost or duplicated elements: %v", c.n, all)
		}
	}
}

func TestGetGroupsLargeInput(t *testing.T) {
	elements := make([]int, 973)
	groups := GetGroups(elements, 10, 10, 10, rand.New(rand.NewPCG(1, 2)))
	if len(groups) != 108 {
		t.Fatalf("len = %d, want 108", len(groups))
	}
	lo, hi := 100, 0
	for _, g := range groups {
		lo, hi = min(lo, len(g)), max(hi, len(g))
	}
	if hi != 10 || lo != 9 {
		t.Errorf("sizes in [%d, %d], want [9, 10]", lo, hi)
	}
}

func TestGetGroupsAllCompanySizes(t *testing.T) {
	rng := rand.New(rand.NewPCG(3, 4))
	for n := 0; n <= 400; n++ {
		groups := GetGroups(make([]int, n), 6, 5, 7, rng)
		if len(groups) < 1 {
			t.Fatalf("n=%d: no groups", n)
		}
		for _, g := range groups {
			if len(g) > 7 {
				t.Fatalf("n=%d: group of %d", n, len(g))
			}
		}
	}
}

func TestFormGroupsGroupsByYesAnswerInChoiceOrder(t *testing.T) {
	choices := []Choice{
		{Key: "yes_1145", IsYes: true, Time: "11:45"},
		{Key: "yes_1230", IsYes: true, Time: "12:30"},
		NoChoice,
	}
	responses := []Response{
		{UserID: "a", ResponseKey: "yes_1230"},
		{UserID: "b", ResponseKey: "yes_1145"},
		{UserID: "c", ResponseKey: "no"},
		{UserID: "d", ResponseKey: "yes_1145"},
		{UserID: "e", ResponseKey: "bogus"},
	}
	groups := FormGroups(choices, responses, 6, rand.New(rand.NewPCG(0, 0)))
	if len(groups) != 2 {
		t.Fatalf("groups = %+v", groups)
	}
	if groups[0].ResponseKey != "yes_1145" || !reflect.DeepEqual(groups[0].UserIDs, []string{"b", "d"}) {
		t.Errorf("groups[0] = %+v", groups[0])
	}
	if groups[1].ResponseKey != "yes_1230" || !reflect.DeepEqual(groups[1].UserIDs, []string{"a"}) {
		t.Errorf("groups[1] = %+v", groups[1])
	}
}

func TestMessages(t *testing.T) {
	choice := Choice{Key: "yes_1200", IsYes: true, Time: "12:00", DisplayText: "Yes (12:00)"}
	if got := InChannelGroupMessage(choice, []string{"U1", "U2"}); got != "Hey <@U1>, <@U2>! This is your group for today. You all should meet somewhere at `12:00`." {
		t.Errorf("InChannelGroupMessage = %q", got)
	}
	if got := Intersect([]string{"c", "a", "b"}, []string{"b", "x", "a", "a"}); !reflect.DeepEqual(got, []string{"a", "b"}) {
		t.Errorf("Intersect = %v", got)
	}
	att := PollAttachments("cb", DefaultChoices())
	if att[0]["callback_id"] != "cb" || len(att[0]["actions"].([]map[string]any)) != 2 {
		t.Errorf("PollAttachments = %+v", att)
	}
}

func TestHelpTextDescribesCurrentBehaviour(t *testing.T) {
	for _, want := range []string{"@Lunch Buddies create", "@Lunch Buddies close", "size=4", "announces each group in the channel", "support@lunchbuddiesapp.com"} {
		if !strings.Contains(AppExplanation, want) {
			t.Errorf("help text should mention %q", want)
		}
	}
	// Removed features must not be advertised.
	for _, gone := range []string{"private group", "summary", "customize by saying"} {
		if strings.Contains(strings.ToLower(AppExplanation), gone) {
			t.Errorf("help text still mentions %q", gone)
		}
	}
}
