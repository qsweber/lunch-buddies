// Package invoice is a port of actions/invoice.py: bill each eligible team for the unique
// users who answered "yes" to its polls since its last invoice.
package invoice

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/stripe"
)

// PricePerYesUserCents preserves the Python behaviour exactly: it passed `amount=1.0 * users`
// to Stripe, whose amounts are in cents, i.e. one cent per user. The Python handler also
// always ran with dry_run=True, so this has never actually billed anyone. Confirm the
// intended price before running with DryRun=false (design doc open question).
const PricePerYesUserCents = 1

type Input struct {
	// DryRun defaults to true when omitted.
	DryRun *bool `json:"dry_run"`
}

type Deps struct {
	Repositories repositories.Repositories
	Stripe       stripe.API
	Now          func() time.Time
}

func (d Deps) Run(ctx context.Context, in Input) error {
	dryRun := in.DryRun == nil || *in.DryRun
	teams, err := d.eligibleTeams(ctx)
	if err != nil {
		return err
	}
	for _, team := range teams {
		if err := d.invoiceTeam(ctx, team, dryRun); err != nil {
			return fmt.Errorf("team %s: %w", team.TeamID, err)
		}
	}
	return nil
}

func (d Deps) eligibleTeams(ctx context.Context) ([]repositories.Team, error) {
	now := d.Now()
	temp := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC).AddDate(0, 0, -15)
	atLeastOneFullMonthAgo := time.Date(temp.Year(), temp.Month(), 1, 0, 0, 0, 0, time.UTC)

	all, err := d.Repositories.Teams.ListTeams(ctx)
	if err != nil {
		return nil, err
	}
	var eligible []repositories.Team
	for _, t := range all {
		if t.StripeCustomerID != "" && t.InvoicingEnabled && time.UnixMilli(t.CreatedAt).Before(atLeastOneFullMonthAgo) {
			eligible = append(eligible, t)
		}
	}
	return eligible, nil
}

func (d Deps) invoiceTeam(ctx context.Context, team repositories.Team, dryRun bool) error {
	freeUntil := time.UnixMilli(team.CreatedAt).AddDate(0, 0, 30)
	candidates, err := d.Repositories.Polls.ListPollsForTeam(ctx, team.TeamID, freeUntil)
	if err != nil {
		return err
	}

	var billable []repositories.Poll
	yesUsers := map[string]bool{}
	for _, p := range candidates {
		closed := p.State == repositories.StateClosed || p.State == repositories.StateComplete
		if !closed || p.StripeInvoiceID != "" || p.CreatedAt <= freeUntil.UnixMilli() {
			continue
		}
		billable = append(billable, p)
		collection, err := d.Repositories.Polls.GetPollCollection(ctx, p.CallbackID)
		if err != nil {
			return err
		}
		for _, r := range collection.Responses {
			if strings.Contains(r.Response, "yes") {
				yesUsers[r.UserID] = true
			}
		}
	}

	if len(yesUsers) == 0 {
		slog.Info("no need to invoice team", "team", team.Name)
		return nil
	}

	since := freeUntil
	latest, err := d.Stripe.LatestInvoice(ctx, team.StripeCustomerID)
	if err != nil {
		return err
	}
	if latest != nil {
		since = latest.CreatedAt
	}
	item := stripe.LineItem{
		AmountCents: int64(len(yesUsers) * PricePerYesUserCents),
		Description: fmt.Sprintf("%d people responded Yes to a Lunch Buddies poll since %s", len(yesUsers), since.Format("2006-01-02")),
	}

	if dryRun {
		slog.Info("dry run: would invoice team", "team", team.Name, "amount_cents", item.AmountCents, "description", item.Description)
		return nil
	}

	invoice, err := d.Stripe.CreateInvoice(ctx, team.StripeCustomerID, []stripe.LineItem{item})
	if err != nil || invoice == nil {
		return err
	}
	for _, p := range billable {
		if err := d.Repositories.Polls.SetStripeInvoiceID(ctx, p.CallbackID, invoice.ID); err != nil {
			return err
		}
	}
	return nil
}
