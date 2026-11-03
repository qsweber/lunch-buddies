package server

import (
	"context"
	"crypto/rand"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"time"

	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/kms"

	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/slack"
	"github.com/qsweber/lunch-buddies/internal/slackverify"
	"github.com/qsweber/lunch-buddies/internal/stripe"
	"github.com/qsweber/lunch-buddies/internal/tokencipher"
)

// Config holds deployment settings that come from environment variables.
type Config struct {
	// AuthURL is the Slack "Add to Slack" authorize URL that /install redirects to.
	AuthURL string
	// RegistrationURL is where /auth redirects after a successful install.
	RegistrationURL string
	ClientID        string
	ClientSecret    string
}

// ServiceContext is built once per Lambda cold start and shared by every request.
type ServiceContext struct {
	Repositories repositories.Repositories
	Slack        slack.API
	Stripe       stripe.API
	Verifier     slackverify.Verifier
	Config       Config
	Now          func() time.Time
	NewID        func() string
}

// NewServiceContext wires real AWS, Slack and Stripe clients from the environment.
func NewServiceContext(ctx context.Context) (ServiceContext, error) {
	cfg, err := awsconfig.LoadDefaultConfig(ctx)
	if err != nil {
		return ServiceContext{}, fmt.Errorf("failed to load AWS config: %w", err)
	}

	table := os.Getenv("RECORDS_TABLE")
	if table == "" {
		return ServiceContext{}, errors.New("RECORDS_TABLE environment variable is not set")
	}
	keyID := os.Getenv("TOKEN_KMS_KEY_ID")
	if keyID == "" {
		return ServiceContext{}, errors.New("TOKEN_KMS_KEY_ID environment variable is not set")
	}

	sc := ServiceContext{
		Repositories: repositories.New(table, dynamodb.NewFromConfig(cfg), tokencipher.NewKMS(kms.NewFromConfig(cfg), keyID)),
		Slack:        slack.New(),
		Stripe:       stripe.New(os.Getenv("STRIPE_API_KEY")),
		Verifier: slackverify.Verifier{
			SigningSecret: os.Getenv("SLACK_SIGNING_SECRET"),
			LegacyTokens:  []string{os.Getenv("SLACK_VERIFICATION_TOKEN")},
		},
		Config: Config{
			AuthURL:         os.Getenv("AUTH_URL"),
			RegistrationURL: envOr("REGISTRATION_URL", "https://www.lunchbuddiesapp.com/registration/"),
			ClientID:        os.Getenv("SLACK_CLIENT_ID"),
			ClientSecret:    os.Getenv("SLACK_CLIENT_SECRET"),
		},
		Now:   time.Now,
		NewID: NewUUID,
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
