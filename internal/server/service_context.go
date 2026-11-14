package server

import (
	"context"
	"crypto/rand"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"strings"
	"time"

	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/ssm"

	"github.com/qsweber/lunch-buddies/internal/params"
	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/slack"
	"github.com/qsweber/lunch-buddies/internal/slackverify"
)

// Config holds deployment settings (from SSM Parameter Store, or env vars when running locally).
type Config struct {
	// APIBaseURL is this API's public base URL (e.g. https://api.lunchbuddiesapp.com). The
	// OAuth redirect URI is APIBaseURL + /v1/auth.
	APIBaseURL string
	// RegistrationURL is where /auth redirects after a successful install.
	RegistrationURL string
	ClientID        string
	ClientSecret    string
}

// ServiceContext is built once per Lambda cold start and shared by every request.
type ServiceContext struct {
	Repositories repositories.Repositories
	Slack        slack.API
	Verifier     slackverify.Verifier
	Config       Config
	Now          func() time.Time
	NewID        func() string
	// Forwarder, when set, passes Slack requests through to the legacy Zappa API instead of
	// handling them (cutover forwarding mode; see forward.go).
	Forwarder *Forwarder
}

// NewServiceContext wires real AWS and Slack clients. When PARAMETER_PREFIX is set (as it is
// in the deployed Lambda), Slack settings are read from SSM Parameter Store under that prefix
// at cold start; otherwise they come from env vars of the same name in upper case, for local
// runs.
func NewServiceContext(ctx context.Context) (ServiceContext, error) {
	cfg, err := awsconfig.LoadDefaultConfig(ctx)
	if err != nil {
		return ServiceContext{}, fmt.Errorf("failed to load AWS config: %w", err)
	}

	table := os.Getenv("RECORDS_TABLE")
	if table == "" {
		return ServiceContext{}, errors.New("RECORDS_TABLE environment variable is not set")
	}

	setting := func(key string) string { return os.Getenv(strings.ToUpper(key)) }
	if prefix := os.Getenv("PARAMETER_PREFIX"); prefix != "" {
		values, err := params.Load(ctx, ssm.NewFromConfig(cfg), prefix, params.Required)
		if err != nil {
			return ServiceContext{}, err
		}
		setting = func(key string) string { return values[key] }
		slog.Info("loaded settings from SSM", "prefix", prefix)
	}

	sc := ServiceContext{
		Repositories: repositories.New(table, dynamodb.NewFromConfig(cfg)),
		Slack:        slack.New(),
		Verifier: slackverify.Verifier{
			SigningSecret: setting(params.SlackSigningSecret),
			LegacyTokens:  []string{setting(params.SlackVerificationToken)},
		},
		Config: Config{
			APIBaseURL:      strings.TrimRight(os.Getenv("API_BASE_URL"), "/"),
			RegistrationURL: envOr("REGISTRATION_URL", "https://www.lunchbuddiesapp.com/registration/"),
			ClientID:        setting(params.SlackClientID),
			ClientSecret:    setting(params.SlackClientSecret),
		},
		Now:   time.Now,
		NewID: NewUUID,
	}
	if legacy := setting(params.LegacyForwardURL); legacy != "" {
		sc.Forwarder = NewForwarder(legacy)
		slog.Warn("FORWARDING MODE: passing Slack requests through to the legacy API", "legacy_url", legacy)
	}
	slog.Info("initialized service context", "table", table)
	return sc, nil
}

func envOr(name, fallback string) string {
	if v := os.Getenv(name); v != "" {
		return v
	}
	return fallback
}

// NewUUID returns a random RFC 4122 version 4 UUID, the same shape as Python's uuid4().
func NewUUID() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		panic(err)
	}
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
