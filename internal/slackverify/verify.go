// Package slackverify authenticates requests from Slack.
//
// The preferred mechanism is the v0 request signature (HMAC-SHA256 of
// "v0:<timestamp>:<raw body>" with the app's signing secret). For the transition from the
// Python app, which used the legacy verification token, a request is also accepted if it
// carries one of the configured legacy tokens and has no signature to check.
package slackverify

import (
	"crypto/hmac"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"errors"
	"math"
	"strconv"
	"time"
)

// MaxClockSkew bounds replay of a captured signed request.
const MaxClockSkew = 5 * time.Minute

var ErrUnauthorized = errors.New("request is not from Slack")

type Verifier struct {
	SigningSecret string
	LegacyTokens  []string
	Now           func() time.Time
}

// Verify checks the request. headers must use lowercase names (as HTTP API v2 delivers
// them); token is the legacy "token" field from the body, if any.
func (v Verifier) Verify(headers map[string]string, body string, token string) error {
	signature := headers["x-slack-signature"]
	timestamp := headers["x-slack-request-timestamp"]

	if v.SigningSecret != "" && signature != "" {
		ts, err := strconv.ParseInt(timestamp, 10, 64)
		if err != nil {
			return ErrUnauthorized
		}
		now := time.Now
		if v.Now != nil {
			now = v.Now
		}
		if math.Abs(float64(now().Unix()-ts)) > MaxClockSkew.Seconds() {
			return ErrUnauthorized
		}
		mac := hmac.New(sha256.New, []byte(v.SigningSecret))
		mac.Write([]byte("v0:" + timestamp + ":" + body))
		expected := "v0=" + hex.EncodeToString(mac.Sum(nil))
		if hmac.Equal([]byte(expected), []byte(signature)) {
			return nil
		}
		return ErrUnauthorized
	}

	if token != "" {
		for _, allowed := range v.LegacyTokens {
			if allowed != "" && subtle.ConstantTimeCompare([]byte(allowed), []byte(token)) == 1 {
				return nil
			}
		}
	}
	return ErrUnauthorized
}
