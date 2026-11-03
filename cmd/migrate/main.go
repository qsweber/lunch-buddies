// Command migrate copies the legacy Python tables into the single records table. It is
// safe to re-run: every write is conditional on the item not existing, so newer data is never
// overwritten. Nothing it writes triggers a workflow (polls are inserted as OPEN or
// COMPLETE, never REQUESTED).
//
//	go run ./cmd/migrate -target lunch-buddies-prod-records -kms-key alias/lunch-buddies-prod-tokens -dry-run
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log"
	"strconv"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/aws/aws-sdk-go-v2/service/kms"

	"github.com/qsweber/lunch-buddies/internal/migrate"
	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/tokencipher"
)

func main() {
	var (
		teamsTable     = flag.String("teams-table", "lunch_buddies_Team", "legacy teams table")
		pollsTable     = flag.String("polls-table", "lunch_buddies_Poll", "legacy polls table")
		responsesTable = flag.String("responses-table", "lunch_buddies_PollResponse", "legacy responses table")
		groupsTable    = flag.String("groups-table", "lunch_buddies_Group", "legacy groups table")
		target         = flag.String("target", "", "single records table to write (required)")
		kmsKey         = flag.String("kms-key", "", "KMS key id/alias for bot tokens (required)")
		dryRun         = flag.Bool("dry-run", true, "only read and transform; print counts")
	)
	flag.Parse()
	if *target == "" || *kmsKey == "" {
		log.Fatal("-target and -kms-key are required")
	}

	ctx := context.Background()
	cfg, err := awsconfig.LoadDefaultConfig(ctx)
	if err != nil {
		log.Fatal(err)
	}
	db := dynamodb.NewFromConfig(cfg)
	teamsRepo := repositories.NewTeamsRepository(*target, db, tokencipher.NewKMS(kms.NewFromConfig(cfg), *kmsKey))
	w := writer{db: db, table: *target, dryRun: *dryRun, counts: map[string][2]int{}}

	// Groups first, so each closed poll can record its group count.
	groupCounts := map[string]int{}
	var groups []repositories.Group
	must(scan(ctx, db, *groupsTable, func(r migrate.Row) error {
		g, err := migrate.Group(r)
		if err != nil {
			return err
		}
		groups = append(groups, g)
		groupCounts[g.CallbackID]++
		return nil
	}))

	must(scan(ctx, db, *teamsTable, func(r migrate.Row) error {
		team, err := migrate.Team(r)
		if err != nil {
			return err
		}
		if *dryRun {
			w.count("team", true)
			return nil
		}
		existing, err := teamsRepo.GetTeam(ctx, team.TeamID)
		if err != nil {
			return err
		}
		if existing != nil {
			w.count("team", false)
			return nil
		}
		w.count("team", true)
		return teamsRepo.PutTeam(ctx, team)
	}))

	var allPolls []repositories.Poll
	must(scan(ctx, db, *pollsTable, func(r migrate.Row) error {
		p, err := migrate.Poll(r, groupCounts[fmt.Sprint(r["callback_id"])])
		if err != nil {
			return err
		}
		allPolls = append(allPolls, p)
		return w.put(ctx, "poll", p.WithKeys())
	}))

	for _, a := range migrate.ActivePointers(allPolls) {
		must(w.put(ctx, "active_poll", a))
	}

	must(scan(ctx, db, *responsesTable, func(r migrate.Row) error {
		resp, err := migrate.Response(r)
		if err != nil {
			return err
		}
		return w.put(ctx, "response", resp)
	}))

	for _, g := range groups {
		must(w.put(ctx, "group", g))
	}

	mode := "WROTE"
	if *dryRun {
		mode = "DRY RUN (would write)"
	}
	fmt.Printf("%s to %s:\n", mode, *target)
	for _, kind := range []string{"team", "poll", "active_poll", "response", "group"} {
		c := w.counts[kind]
		fmt.Printf("  %-12s new=%d already-present=%d\n", kind, c[0], c[1])
	}
}

type writer struct {
	db     *dynamodb.Client
	table  string
	dryRun bool
	counts map[string][2]int
}

func (w *writer) count(kind string, isNew bool) {
	c := w.counts[kind]
	if isNew {
		c[0]++
	} else {
		c[1]++
	}
	w.counts[kind] = c
}

func (w *writer) put(ctx context.Context, kind string, item any) error {
	if w.dryRun {
		w.count(kind, true)
		return nil
	}
	av, err := attributevalue.MarshalMap(item)
	if err != nil {
		return err
	}
	_, err = w.db.PutItem(ctx, &dynamodb.PutItemInput{
		TableName:           aws.String(w.table),
		Item:                av,
		ConditionExpression: aws.String("attribute_not_exists(pk)"),
	})
	var ccf *types.ConditionalCheckFailedException
	if errors.As(err, &ccf) {
		w.count(kind, false)
		return nil
	}
	if err == nil {
		w.count(kind, true)
	}
	return err
}

// scan reads every item of a legacy table. Numbers are converted to their decimal string
// form so timestamps keep full precision.
func scan(ctx context.Context, db *dynamodb.Client, table string, fn func(migrate.Row) error) error {
	p := dynamodb.NewScanPaginator(db, &dynamodb.ScanInput{TableName: aws.String(table), ConsistentRead: aws.Bool(true)})
	for p.HasMorePages() {
		page, err := p.NextPage(ctx)
		if err != nil {
			return fmt.Errorf("scanning %s: %w", table, err)
		}
		for _, item := range page.Items {
			row := migrate.Row{}
			for k, v := range item {
				row[k] = plain(v)
			}
			if err := fn(row); err != nil {
				return fmt.Errorf("%s: %w", table, err)
			}
		}
	}
	return nil
}

func plain(v types.AttributeValue) any {
	switch t := v.(type) {
	case *types.AttributeValueMemberS:
		return t.Value
	case *types.AttributeValueMemberN:
		return t.Value
	case *types.AttributeValueMemberBOOL:
		return strconv.FormatBool(t.Value)
	case *types.AttributeValueMemberNULL:
		return nil
	default:
		return fmt.Sprint(t)
	}
}

func must(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
