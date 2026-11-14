// Package workflows holds the logic behind the DynamoDB stream router and the Step Functions
// task Lambdas. Each cmd/<task>/main.go is a thin wrapper that builds Deps and calls one
// function here.
package workflows

import (
	"context"
	cryptorand "crypto/rand"
	"encoding/binary"
	"errors"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"os"
	"time"

	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"

	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/slack"
)

// Deps are the dependencies shared by the task Lambdas.
type Deps struct {
	Repositories repositories.Repositories
	Slack        slack.API
	Now          func() time.Time
	Rand         *rand.Rand
}

// NewDepsFromEnv wires real clients. Used by every task Lambda's main.
func NewDepsFromEnv(ctx context.Context) (Deps, error) {
	cfg, err := awsconfig.LoadDefaultConfig(ctx)
	if err != nil {
		return Deps{}, fmt.Errorf("failed to load AWS config: %w", err)
	}
	table := os.Getenv("RECORDS_TABLE")
	if table == "" {
		return Deps{}, errors.New("RECORDS_TABLE must be set")
	}
	return Deps{
		Repositories: repositories.New(table, dynamodb.NewFromConfig(cfg)),
		Slack:        slack.New(),
		Now:          time.Now,
		Rand:         NewRand(),
	}, nil
}

// NewRand returns a randomly seeded generator for shuffling groups.
func NewRand() *rand.Rand {
	var seed [32]byte
	_, _ = cryptorand.Read(seed[:])
	return rand.New(rand.NewChaCha8(seed))
}

// dm posts a direct message, ignoring channel_not_found (the user may have left), like the
// Python post_message_if_channel_exists.
func (d Deps) dm(ctx context.Context, token, userID, text string) error {
	if userID == "" {
		return nil
	}
	_, err := d.Slack.PostMessage(ctx, token, slack.Message{Channel: userID, Text: text, AsUser: true})
	if errors.Is(err, slack.ErrChannelNotFound) {
		slog.Warn("could not DM user; channel not found", "user", userID)
		return nil
	}
	return err
}

func (d Deps) loadTeam(ctx context.Context, teamID string) (*repositories.Team, error) {
	team, err := d.Repositories.Teams.GetTeam(ctx, teamID)
	if err != nil {
		return nil, err
	}
	if team == nil {
		return nil, fmt.Errorf("team %s not found", teamID)
	}
	if !team.Installed() {
		return nil, fmt.Errorf("team %s has uninstalled the app", teamID)
	}
	return team, nil
}

func randomChoice(r *rand.Rand, items []string) string {
	return items[r.IntN(len(items))]
}

func seededForTest(seed uint64) *rand.Rand {
	var b [32]byte
	binary.LittleEndian.PutUint64(b[:], seed)
	return rand.New(rand.NewChaCha8(b))
}
