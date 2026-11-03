package polls

import (
	"math/rand/v2"
)

// Response is the minimal view of a poll response needed for grouping.
type Response struct {
	UserID      string
	ResponseKey string
}

// Group is a set of users who answered the same "yes" choice.
type Group struct {
	ResponseKey string
	UserIDs     []string
}

// FormGroups splits the "yes" respondents of each choice into groups of roughly
// groupSize. Choices are processed in poll order so the output is stable for a given rng.
// Responses whose key isn't a "yes" choice on the poll are ignored.
func FormGroups(choices []Choice, responses []Response, groupSize int, rng *rand.Rand) []Group {
	byKey := map[string][]string{}
	for _, r := range responses {
		choice := FindChoice(choices, r.ResponseKey)
		if choice == nil || !choice.IsYes {
			continue
		}
		byKey[r.ResponseKey] = append(byKey[r.ResponseKey], r.UserID)
	}

	minGroupSize := max(1, groupSize-1)

	var groups []Group
	for _, choice := range choices {
		userIDs, ok := byKey[choice.Key]
		if !ok {
			continue
		}
		for _, members := range GetGroups(userIDs, groupSize, minGroupSize, MaxGroupSize, rng) {
			groups = append(groups, Group{ResponseKey: choice.Key, UserIDs: members})
		}
	}
	return groups
}

// GetGroups is a direct port of the Python _get_groups algorithm: shuffle, chunk into
// groupSize, and if the last chunk is smaller than minGroupSize either spread its members
// over the other groups (if that keeps them within maxGroupSize) or retry with a smaller
// group size.
func GetGroups[T any](elements []T, groupSize, minGroupSize, maxGroupSize int, rng *rand.Rand) [][]T {
	if len(elements) <= groupSize {
		return [][]T{append([]T(nil), elements...)}
	}

	shuffled := append([]T(nil), elements...)
	rng.Shuffle(len(shuffled), func(i, j int) { shuffled[i], shuffled[j] = shuffled[j], shuffled[i] })

	var groups [][]T
	for i := 0; i < len(shuffled); i += groupSize {
		end := min(i+groupSize, len(shuffled))
		groups = append(groups, append([]T(nil), shuffled[i:end]...))
	}

	if len(groups[len(groups)-1]) < minGroupSize {
		last := groups[len(groups)-1]
		groups = groups[:len(groups)-1]

		if (maxGroupSize-groupSize)*len(groups) >= len(last) {
			i := 0
			for len(last) > 0 {
				groups[i] = append(groups[i], last[len(last)-1])
				last = last[:len(last)-1]
				if i >= len(groups)-1 {
					i = 0
				} else {
					i++
				}
			}
		} else {
			return GetGroups(elements, groupSize-1, min(groupSize-1, minGroupSize), maxGroupSize, rng)
		}
	}

	return groups
}
