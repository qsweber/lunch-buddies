// Command migrate copies teams (and their bot tokens) from the legacy Python app's
// lunch_buddies_Team table into the single records table, for the production cutover. Old
// polls, responses and groups are deliberately not copied.
//
// It first refuses to run if any legacy poll is in flight (still CREATED and created within
// -in-flight-window), because that poll's buttons and close would then reach a new system
// that has never heard of it. The check runs in dry-run mode too, so a dry run tells you
// whether now is a good time to cut over.
//
// Re-running is safe: a team already in the target table is left alone.
//
//	go run ./cmd/migrate -target lunch-buddies-prod-records                 # dry run
//	go run ./cmd/migrate -target lunch-buddies-prod-records -dry-run=false  # copy teams
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"strconv"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"

	"github.com/qsweber/lunch-buddies/internal/migrate"
	"github.com/qsweber/lunch-buddies/internal/repositories"
)

func main() {
	var (
		teamsTable = flag.String("teams-table", "lunch_buddies_Team", "legacy teams table")
		pollsTable = flag.String("polls-table", "lunch_buddies_Poll", "legacy polls table, checked for polls in flight")
		target     = flag.String("target", "", "single records table to write teams into (required)")
		window     = flag.Duration("in-flight-window", 24*time.Hour, "a CREATED legacy poll newer than this counts as in flight")
		dryRun     = flag.Bool("dry-run", true, "check and count only; write nothing")
	)
	flag.Parse()
	if *target == "" {
		log.Fatal("-target is required")
	}

	ctx := context.Background()
	cfg, err := awsconfig.LoadDefaultConfig(ctx)
	if err != nil {
		log.Fatal(err)
	}
	db := dynamodb.NewFromConfig(cfg)

	// 1. Refuse to cut over while a legacy poll is in flight.
	var pollRows []migrate.Row
	must(scan(ctx, db, *pollsTable, func(r migrate.Row) { pollRows = append(pollRows, r) }))
	inFlight, stale, err := migrate.InFlight(pollRows, time.Now(), *window)
	must(err)
	if len(stale) > 0 {
		fmt.Printf("Ignoring %d abandoned CREATED poll(s) older than %s (they won't be closable after cutover):\n", len(stale), *window)
		for _, p := range stale {
			fmt.Println("  ", p)
		}
	}
	if len(inFlight) > 0 {
		fmt.Fprintf(os.Stderr, "REFUSING: %d legacy poll(s) in flight (CREATED within the last %s). Wait until they're closed, then try again:\n", len(inFlight), *window)
		for _, p := range inFlight {
			fmt.Fprintln(os.Stderr, "  ", p)
		}
		os.Exit(1)
	}
	fmt.Printf("No legacy polls in flight (checked %d polls).\n", len(pollRows))

	// 2. Copy teams that aren't in the target table yet.
	teams := repositories.NewTeamsRepository(*target, db)
	var copied, present int
	must(scan(ctx, db, *teamsTable, func(r migrate.Row) {
		team, err := migrate.Team(r)
		must(err)
		existing, err := teams.GetTeam(ctx, team.TeamID)
		must(err)
		if existing != nil {
			present++
			return
		}
		copied++
		if !*dryRun {
			must(teams.PutTeam(ctx, team))
		}
	}))

	if *dryRun {
		fmt.Printf("DRY RUN: would copy %d team(s) into %s; %d already there.\n", copied, *target, present)
	} else {
		fmt.Printf("Copied %d team(s) into %s; %d already there.\n", copied, *target, present)
	}
}

// scan reads every item of a legacy table. Numbers keep their decimal text so timestamps
// keep full precision.
func scan(ctx context.Context, db *dynamodb.Client, table string, fn func(migrate.Row)) error {
	p := dynamodb.NewScanPaginator(db, &dynamodb.ScanInput{TableName: aws.String(table), ConsistentRead: aws.Bool(true)})
	for p.HasMorePages() {
		page, err := p.NextPage(ctx)
		if err != nil {
			return fmt.Errorf("scanning %s: %w", table, err)
		}
		for _, item := range page.Items {
			row := migrate.Row{}
			for k, v := range item {
				switch t := v.(type) {
				case *types.AttributeValueMemberS:
					row[k] = t.Value
				case *types.AttributeValueMemberN:
					row[k] = t.Value
				case *types.AttributeValueMemberBOOL:
					row[k] = strconv.FormatBool(t.Value)
				}
			}
			fn(row)
		}
	}
	return nil
}

func must(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
