package slackverify

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"testing"
	"time"
)

func sign(secret, ts, body string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte("v0:" + ts + ":" + body))
	return "v0=" + hex.EncodeToString(mac.Sum(nil))
}

func TestVerify(t *testing.T) {
	now := time.Unix(1700000000, 0)
	v := Verifier{SigningSecret: "s3cret", LegacyTokens: []string{"legacy", ""}, Now: func() time.Time { return now }}
	body := "token=x&team_id=T1"

	headers := func(ts, sig string) map[string]string {
		return map[string]string{"x-slack-request-timestamp": ts, "x-slack-signature": sig}
	}

	cases := []struct {
		name    string
		headers map[string]string
		token   string
		ok      bool
	}{
		{"valid signature", headers("1700000000", sign("s3cret", "1700000000", body)), "", true},
		{"wrong secret", headers("1700000000", sign("nope", "1700000000", body)), "", false},
		{"stale timestamp", headers("1699999000", sign("s3cret", "1699999000", body)), "", false},
		{"bad signature ignores valid legacy token", headers("1700000000", "v0=deadbeef"), "legacy", false},
		{"legacy token without signature", map[string]string{}, "legacy", true},
		{"wrong legacy token", map[string]string{}, "other", false},
		{"empty token never matches empty configured token", map[string]string{}, "", false},
	}
	for _, c := range cases {
		err := v.Verify(c.headers, body, c.token)
		if (err == nil) != c.ok {
			t.Errorf("%s: err = %v, want ok=%v", c.name, err, c.ok)
		}
	}
}
