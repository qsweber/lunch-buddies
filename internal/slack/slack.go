// Package slack is a small Slack Web API client covering only the methods Lunch Buddies uses.
// It sits behind the API interface so services can be tested with a fake.
package slack

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

// ErrChannelNotFound is returned when Slack reports channel_not_found.
var ErrChannelNotFound = errors.New("slack: channel_not_found")

// APIError is any other `"ok": false` response.
type APIError struct {
	Method string
	Code   string
}

func (e *APIError) Error() string { return fmt.Sprintf("slack %s: %s", e.Method, e.Code) }

// RateLimitedError is returned on HTTP 429. Its type name is what Step Functions Retry
// policies match on (aws-lambda-go reports the error's type name as errorType).
type RateLimitedError struct {
	Method     string
	RetryAfter time.Duration
}

func (e *RateLimitedError) Error() string {
	return fmt.Sprintf("slack %s: rate limited, retry after %s", e.Method, e.RetryAfter)
}

type Message struct {
	Channel     string           `json:"channel"`
	Text        string           `json:"text"`
	ThreadTS    string           `json:"thread_ts,omitempty"`
	Attachments []map[string]any `json:"attachments,omitempty"`
	// AsUser mirrors the Python client, which always sent as_user=true.
	AsUser bool `json:"as_user,omitempty"`
}

type Channel struct {
	ID   string
	Name string
}

type User struct {
	Name  string
	Email string
	TZ    string
}

type OAuthAccess struct {
	AccessToken string
	TeamID      string
	TeamName    string
	UserID      string
}

// API is the Slack surface Lunch Buddies uses.
type API interface {
	PostMessage(ctx context.Context, token string, msg Message) (ts string, err error)
	OpenConversation(ctx context.Context, token string, userIDs []string) (channelID string, err error)
	ConversationMembers(ctx context.Context, token, channelID string) ([]string, error)
	// FindChannelByName returns nil if no channel has that name.
	FindChannelByName(ctx context.Context, token, name string) (*Channel, error)
	UserInfo(ctx context.Context, token, userID string) (*User, error)
	// OAuthV2Access exchanges an install code for a bot token. redirectURI must be the one
	// used on the authorize URL.
	OAuthV2Access(ctx context.Context, clientID, clientSecret, code, redirectURI string) (*OAuthAccess, error)
}

type Client struct {
	BaseURL    string
	HTTPClient *http.Client
}

func New() *Client {
	return &Client{BaseURL: "https://slack.com/api/", HTTPClient: &http.Client{Timeout: 10 * time.Second}}
}

type envelope struct {
	OK               bool   `json:"ok"`
	Error            string `json:"error"`
	ResponseMetadata struct {
		NextCursor string `json:"next_cursor"`
	} `json:"response_metadata"`
}

// call POSTs to method. Either jsonBody or form is used. The response is decoded into out,
// which must embed envelope-compatible fields (ok, error).
func (c *Client) call(ctx context.Context, method, token string, jsonBody any, form url.Values, out any) error {
	var body io.Reader
	contentType := "application/x-www-form-urlencoded"
	if jsonBody != nil {
		b, err := json.Marshal(jsonBody)
		if err != nil {
			return err
		}
		body = bytes.NewReader(b)
		contentType = "application/json; charset=utf-8"
	} else {
		body = strings.NewReader(form.Encode())
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+method, body)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", contentType)
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusTooManyRequests {
		secs, _ := strconv.Atoi(resp.Header.Get("Retry-After"))
		return &RateLimitedError{Method: method, RetryAfter: time.Duration(max(secs, 1)) * time.Second}
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("slack %s: HTTP %d", method, resp.StatusCode)
	}
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	var env envelope
	if err := json.Unmarshal(raw, &env); err != nil {
		return fmt.Errorf("slack %s: decoding response: %w", method, err)
	}
	if !env.OK {
		if env.Error == "channel_not_found" {
			return ErrChannelNotFound
		}
		if env.Error == "ratelimited" {
			return &RateLimitedError{Method: method, RetryAfter: time.Second}
		}
		return &APIError{Method: method, Code: env.Error}
	}
	if out != nil {
		return json.Unmarshal(raw, out)
	}
	return nil
}

func (c *Client) PostMessage(ctx context.Context, token string, msg Message) (string, error) {
	var out struct {
		TS string `json:"ts"`
	}
	if err := c.call(ctx, "chat.postMessage", token, msg, nil, &out); err != nil {
		return "", err
	}
	return out.TS, nil
}

func (c *Client) OpenConversation(ctx context.Context, token string, userIDs []string) (string, error) {
	var out struct {
		Channel struct {
			ID string `json:"id"`
		} `json:"channel"`
	}
	err := c.call(ctx, "conversations.open", token, map[string]string{"users": strings.Join(userIDs, ",")}, nil, &out)
	return out.Channel.ID, err
}

func (c *Client) ConversationMembers(ctx context.Context, token, channelID string) ([]string, error) {
	var members []string
	cursor := ""
	for {
		form := url.Values{"channel": {channelID}, "limit": {"1000"}}
		if cursor != "" {
			form.Set("cursor", cursor)
		}
		var out struct {
			envelope
			Members []string `json:"members"`
		}
		if err := c.call(ctx, "conversations.members", token, nil, form, &out); err != nil {
			return nil, err
		}
		members = append(members, out.Members...)
		cursor = out.ResponseMetadata.NextCursor
		if cursor == "" {
			return members, nil
		}
	}
}

func (c *Client) FindChannelByName(ctx context.Context, token, name string) (*Channel, error) {
	cursor := ""
	for {
		// Public channels only, matching the Python client's conversations.list defaults
		// (listing private channels would need the groups:read scope).
		form := url.Values{"limit": {"1000"}, "exclude_archived": {"true"}}
		if cursor != "" {
			form.Set("cursor", cursor)
		}
		var out struct {
			envelope
			Channels []struct {
				ID   string `json:"id"`
				Name string `json:"name"`
			} `json:"channels"`
		}
		if err := c.call(ctx, "conversations.list", token, nil, form, &out); err != nil {
			return nil, err
		}
		for _, ch := range out.Channels {
			if ch.Name == name {
				return &Channel{ID: ch.ID, Name: ch.Name}, nil
			}
		}
		cursor = out.ResponseMetadata.NextCursor
		if cursor == "" {
			return nil, nil
		}
	}
}

func (c *Client) UserInfo(ctx context.Context, token, userID string) (*User, error) {
	var out struct {
		User struct {
			TZ      string `json:"tz"`
			Profile struct {
				RealName string `json:"real_name"`
				Email    string `json:"email"`
			} `json:"profile"`
		} `json:"user"`
	}
	if err := c.call(ctx, "users.info", token, nil, url.Values{"user": {userID}}, &out); err != nil {
		return nil, err
	}
	return &User{Name: out.User.Profile.RealName, Email: out.User.Profile.Email, TZ: out.User.TZ}, nil
}

func (c *Client) OAuthV2Access(ctx context.Context, clientID, clientSecret, code, redirectURI string) (*OAuthAccess, error) {
	var out struct {
		AccessToken string `json:"access_token"`
		Team        struct {
			ID   string `json:"id"`
			Name string `json:"name"`
		} `json:"team"`
		AuthedUser struct {
			ID string `json:"id"`
		} `json:"authed_user"`
	}
	form := url.Values{"client_id": {clientID}, "client_secret": {clientSecret}, "code": {code}, "redirect_uri": {redirectURI}}
	if err := c.call(ctx, "oauth.v2.access", "", nil, form, &out); err != nil {
		return nil, err
	}
	return &OAuthAccess{AccessToken: out.AccessToken, TeamID: out.Team.ID, TeamName: out.Team.Name, UserID: out.AuthedUser.ID}, nil
}

var _ API = (*Client)(nil)
