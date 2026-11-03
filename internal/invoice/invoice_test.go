package invoice

import (
	"context"
	"testing"
	"time"

	"github.com/qsweber/lunch-buddies/internal/polls"
	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/repositories/memory"
	"github.com/qsweber/lunch-buddies/internal/stripe"
)

type fakeStripe struct{ items []stripe.LineItem }

func (f *fakeStripe) CreateCustomer(context.Context, string, string, string) (*stripe.Customer, error) {
	return nil, nil
}
func (f *fakeStripe) UpdateCustomer(context.Context, string, string, string, string) error {
	return nil
}
func (f *fakeStripe) LatestInvoice(context.Context, string) (*stripe.Invoice, error) { return nil, nil }
func (f *fakeStripe) CreateInvoice(_ context.Context, _ string, items []stripe.LineItem) (*stripe.Invoice, error) {
	f.items = append(f.items, items...)
	return &stripe.Invoice{ID: "in_1"}, nil
}

func TestInvoiceBillsUniqueYesUsersOnClosedPolls(t *testing.T) {
	ctx := context.Background()
	now := time.Date(2026, 11, 3, 0, 0, 0, 0, time.UTC)
	teamCreated := time.Date(2026, 6, 1, 0, 0, 0, 0, time.UTC)
	store := memory.New()
	_ = store.PutTeam(ctx, repositories.Team{TeamID: "T1", BotAccessToken: "x", StripeCustomerID: "cus", InvoicingEnabled: true, CreatedAt: teamCreated.UnixMilli()})
	_ = store.PutTeam(ctx, repositories.Team{TeamID: "T2", BotAccessToken: "x", StripeCustomerID: "", InvoicingEnabled: true, CreatedAt: teamCreated.UnixMilli()})

	addPoll := func(id string, created time.Time, users map[string]string, state string) {
		_ = store.CreateRequestedPoll(ctx, repositories.Poll{CallbackID: id, TeamID: "T1", CreatedAt: created.UnixMilli(), Choices: polls.DefaultChoices()})
		_ = store.OpenPoll(ctx, store.Polls[id], "C-"+id, created)
		for u, r := range users {
			_ = store.RecordResponse(ctx, repositories.PollResponse{CallbackID: id, UserID: u, Response: r})
		}
		if state == repositories.StateClosed {
			a, _ := store.GetActivePoll(ctx, "T1", "C-"+id)
			_ = store.ClosePoll(ctx, *a, "U", created)
		}
	}
	addPoll("free", teamCreated.AddDate(0, 0, 10), map[string]string{"U9": "yes_1200"}, repositories.StateClosed)
	addPoll("p1", now.AddDate(0, 0, -20), map[string]string{"U1": "yes_1200", "U2": "no"}, repositories.StateClosed)
	addPoll("p2", now.AddDate(0, 0, -10), map[string]string{"U1": "yes_1200", "U3": "yes_1200"}, repositories.StateClosed)
	addPoll("open", now.AddDate(0, 0, -1), map[string]string{"U4": "yes_1200"}, repositories.StateOpen)

	f := &fakeStripe{}
	d := Deps{Repositories: store.Repositories(), Stripe: f, Now: func() time.Time { return now }}

	if err := d.Run(ctx, Input{}); err != nil {
		t.Fatal(err)
	}
	if len(f.items) != 0 {
		t.Fatal("dry run (the default) must not create invoices")
	}

	no := false
	if err := d.Run(ctx, Input{DryRun: &no}); err != nil {
		t.Fatal(err)
	}
	if len(f.items) != 1 || f.items[0].AmountCents != 2 {
		t.Fatalf("items = %+v (want U1 and U3 only)", f.items)
	}
	if store.Polls["p1"].StripeInvoiceID != "in_1" || store.Polls["p2"].StripeInvoiceID != "in_1" || store.Polls["open"].StripeInvoiceID != "" {
		t.Error("only billed polls should be marked invoiced")
	}
}
