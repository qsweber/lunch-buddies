// Package slacktest provides a scriptable in-memory slack.API for tests.
package slacktest

import (
	"context"
	"fmt"
	"sync"

	"github.com/qsweber/lunch-buddies/internal/slack"
)

type Fake struct {
	mu sync.Mutex

	// Configuration.
	Members  map[string][]string      // channel id -> member ids
	Channels map[string]slack.Channel // name -> channel
	Users    map[string]slack.User
	OAuth    *slack.OAuthAccess
	// OAuthRedirectURI records the redirect_uri passed to OAuthV2Access.
	OAuthRedirectURI string
	// PostErrors are returned (in order) by PostMessage before it starts succeeding.
	PostErrors []error

	// Recorded calls.
	Posted []slack.Message
	Tokens []string
}

func New() *Fake {
	return &Fake{Members: map[string][]string{}, Channels: map[string]slack.Channel{}, Users: map[string]slack.User{}}
}

func (f *Fake) PostMessage(_ context.Context, token string, msg slack.Message) (string, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if len(f.PostErrors) > 0 {
		err := f.PostErrors[0]
		f.PostErrors = f.PostErrors[1:]
		return "", err
	}
	f.Posted = append(f.Posted, msg)
	f.Tokens = append(f.Tokens, token)
	return fmt.Sprintf("ts-%d", len(f.Posted)), nil
}

func (f *Fake) ConversationMembers(_ context.Context, _ string, channelID string) ([]string, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	m, ok := f.Members[channelID]
	if !ok {
		return nil, slack.ErrChannelNotFound
	}
	return m, nil
}

func (f *Fake) FindChannelByName(_ context.Context, _ string, name string) (*slack.Channel, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	c, ok := f.Channels[name]
	if !ok {
		return nil, nil
	}
	return &c, nil
}

func (f *Fake) UserInfo(_ context.Context, _ string, userID string) (*slack.User, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	u := f.Users[userID]
	return &u, nil
}

func (f *Fake) OAuthV2Access(_ context.Context, _, _, _ string, redirectURI string) (*slack.OAuthAccess, error) {
	f.mu.Lock()
	f.OAuthRedirectURI = redirectURI
	f.mu.Unlock()
	if f.OAuth == nil {
		return nil, &slack.APIError{Method: "oauth.v2.access", Code: "invalid_code"}
	}
	return f.OAuth, nil
}

// PostedTo returns the texts posted to a channel.
func (f *Fake) PostedTo(channel string) []string {
	f.mu.Lock()
	defer f.mu.Unlock()
	var out []string
	for _, m := range f.Posted {
		if m.Channel == channel {
			out = append(out, m.Text)
		}
	}
	return out
}

var _ slack.API = (*Fake)(nil)
