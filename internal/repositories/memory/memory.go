// Package memory is an in-memory implementation of the repositories with the same
// conditional semantics as the DynamoDB one. It's for tests of the HTTP server and workflow
// tasks, so they exercise real state transitions without DynamoDB.
package memory

import (
	"context"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
)

type Store struct {
	mu         sync.Mutex
	Teams      map[string]repositories.Team
	Polls      map[string]repositories.Poll
	Active     map[string]repositories.ActivePoll // key team|channel
	Responses  map[string]map[string]repositories.PollResponse
	Recipients map[string]map[string]repositories.Recipient
	Groups     map[string]map[string]repositories.Group
}

func New() *Store {
	return &Store{
		Teams:      map[string]repositories.Team{},
		Polls:      map[string]repositories.Poll{},
		Active:     map[string]repositories.ActivePoll{},
		Responses:  map[string]map[string]repositories.PollResponse{},
		Recipients: map[string]map[string]repositories.Recipient{},
		Groups:     map[string]map[string]repositories.Group{},
	}
}

// Repositories returns repositories backed by this store.
func (s *Store) Repositories() repositories.Repositories {
	return repositories.Repositories{Teams: s, Polls: s}
}

func activeKey(team, channel string) string { return team + "|" + channel }

func (s *Store) GetTeam(_ context.Context, teamID string) (*repositories.Team, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	t, ok := s.Teams[teamID]
	if !ok {
		return nil, nil
	}
	return &t, nil
}

func (s *Store) PutTeam(_ context.Context, team repositories.Team) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Teams[team.TeamID] = team.WithKeys()
	return nil
}

func (s *Store) ListTeams(context.Context) ([]repositories.Team, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var out []repositories.Team
	for _, t := range s.Teams {
		out = append(out, t)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].TeamID < out[j].TeamID })
	return out, nil
}

func (s *Store) CreateRequestedPoll(_ context.Context, poll repositories.Poll) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.Polls[poll.CallbackID]; ok {
		return repositories.ErrInvalidTransition
	}
	poll.State = repositories.StateRequested
	s.Polls[poll.CallbackID] = poll.WithKeys()
	return nil
}

func (s *Store) GetPoll(_ context.Context, id string) (*repositories.Poll, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.Polls[id]
	if !ok {
		return nil, nil
	}
	return &p, nil
}

func (s *Store) OpenPoll(_ context.Context, poll repositories.Poll, channelID string, now time.Time) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.Polls[poll.CallbackID]
	if !ok || p.State != repositories.StateRequested {
		return repositories.ErrInvalidTransition
	}
	if a, ok := s.Active[activeKey(p.TeamID, channelID)]; ok && a.CreatedAt >= now.Add(-repositories.ActivePollTTL).UnixMilli() {
		return repositories.ErrActivePollExists
	}
	p.State = repositories.StateOpen
	p.ChannelID = channelID
	s.Polls[p.CallbackID] = p
	s.Active[activeKey(p.TeamID, channelID)] = repositories.ActivePoll{
		TeamID: p.TeamID, ChannelID: channelID, CallbackID: p.CallbackID, CreatedAt: p.CreatedAt,
	}.WithKeys()
	return nil
}

func (s *Store) RejectPoll(_ context.Context, id string, reason string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.Polls[id]
	if !ok || p.State != repositories.StateRequested {
		return repositories.ErrInvalidTransition
	}
	p.State = repositories.StateRejected
	p.RejectionReason = reason
	s.Polls[id] = p
	return nil
}

func (s *Store) GetActivePoll(_ context.Context, teamID, channelID string) (*repositories.ActivePoll, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	a, ok := s.Active[activeKey(teamID, channelID)]
	if !ok {
		return nil, nil
	}
	return &a, nil
}

func (s *Store) ListActivePolls(_ context.Context, teamID string) ([]repositories.ActivePoll, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var out []repositories.ActivePoll
	for k, a := range s.Active {
		if strings.HasPrefix(k, teamID+"|") {
			out = append(out, a)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ChannelID < out[j].ChannelID })
	return out, nil
}

func (s *Store) ClosePoll(_ context.Context, active repositories.ActivePoll, userID string, now time.Time) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.Polls[active.CallbackID]
	a, aok := s.Active[activeKey(active.TeamID, active.ChannelID)]
	if !ok || p.State != repositories.StateOpen || !aok || a.CallbackID != active.CallbackID {
		return repositories.ErrPollNotOpen
	}
	p.State = repositories.StateClosed
	p.ClosedByUserID = userID
	p.ClosedAt = now.UnixMilli()
	s.Polls[p.CallbackID] = p
	delete(s.Active, activeKey(active.TeamID, active.ChannelID))
	return nil
}

func (s *Store) RecordResponse(_ context.Context, r repositories.PollResponse) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.Polls[r.CallbackID]
	if !ok || p.State != repositories.StateOpen {
		return repositories.ErrPollNotOpen
	}
	if s.Responses[r.CallbackID] == nil {
		s.Responses[r.CallbackID] = map[string]repositories.PollResponse{}
	}
	s.Responses[r.CallbackID][r.UserID] = r.WithKeys()
	return nil
}

func (s *Store) GetPollCollection(_ context.Context, id string) (*repositories.PollCollection, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	c := &repositories.PollCollection{}
	if p, ok := s.Polls[id]; ok {
		c.Poll = &p
	}
	for _, k := range sortedKeys(s.Responses[id]) {
		c.Responses = append(c.Responses, s.Responses[id][k])
	}
	for _, k := range sortedKeys(s.Recipients[id]) {
		c.Recipients = append(c.Recipients, s.Recipients[id][k])
	}
	for _, k := range sortedKeys(s.Groups[id]) {
		c.Groups = append(c.Groups, s.Groups[id][k])
	}
	return c, nil
}

func (s *Store) GetRecipient(_ context.Context, id, userID string) (*repositories.Recipient, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	r, ok := s.Recipients[id][userID]
	if !ok {
		return nil, nil
	}
	return &r, nil
}

func (s *Store) MarkRecipientSent(_ context.Context, id, userID, ts string, now time.Time) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.Recipients[id] == nil {
		s.Recipients[id] = map[string]repositories.Recipient{}
	}
	s.Recipients[id][userID] = repositories.Recipient{
		PK: repositories.PollPartitionKey(id), SK: repositories.RecipientSortKey(userID),
		UserID: userID, SentAt: now.UnixMilli(), MessageTS: ts,
	}
	return nil
}

func (s *Store) SaveGroups(_ context.Context, id string, groups []polls.Group) ([]repositories.Group, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.Polls[id]
	if !ok || p.State != repositories.StateClosed || p.GroupCount != nil {
		return nil, repositories.ErrInvalidTransition
	}
	if s.Groups[id] == nil {
		s.Groups[id] = map[string]repositories.Group{}
	}
	var stored []repositories.Group
	idx := map[string]int{}
	for _, g := range groups {
		sk := repositories.GroupSortKey(g.ResponseKey, idx[g.ResponseKey])
		idx[g.ResponseKey]++
		group := repositories.Group{PK: repositories.PollPartitionKey(id), SK: sk, CallbackID: id, ResponseKey: g.ResponseKey, UserIDs: g.UserIDs}
		s.Groups[id][sk] = group
		stored = append(stored, group)
	}
	count := len(groups)
	p.GroupCount = &count
	s.Polls[id] = p
	return stored, nil
}

func (s *Store) GetGroup(_ context.Context, id, sk string) (*repositories.Group, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	g, ok := s.Groups[id][sk]
	if !ok {
		return nil, nil
	}
	return &g, nil
}

func (s *Store) MarkGroupNotified(_ context.Context, id, sk string, now time.Time) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	g, ok := s.Groups[id][sk]
	if !ok {
		return repositories.ErrInvalidTransition
	}
	g.NotifiedAt = now.UnixMilli()
	s.Groups[id][sk] = g
	return nil
}

func (s *Store) ListPollsForTeam(_ context.Context, teamID string, since time.Time) ([]repositories.Poll, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var out []repositories.Poll
	for _, p := range s.Polls {
		if p.TeamID == teamID && p.CreatedAt >= since.UnixMilli() {
			out = append(out, p)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].CreatedAt < out[j].CreatedAt })
	return out, nil
}

func (s *Store) SetStripeInvoiceID(_ context.Context, id, invoiceID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	p, ok := s.Polls[id]
	if !ok {
		return repositories.ErrInvalidTransition
	}
	p.StripeInvoiceID = invoiceID
	s.Polls[id] = p
	return nil
}

func sortedKeys[V any](m map[string]V) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// Compile-time checks.
var (
	_ repositories.TeamsRepository = (*Store)(nil)
	_ repositories.PollsRepository = (*Store)(nil)
)
