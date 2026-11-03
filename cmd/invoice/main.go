// Command invoice bills eligible teams via Stripe. It runs in dry-run mode unless invoked
// with {"dry_run": false}.
package main

import (
	"context"
	"log"
	"os"
	"time"

	"github.com/aws/aws-lambda-go/lambda"

	"github.com/qsweber/lunch-buddies/internal/invoice"
	"github.com/qsweber/lunch-buddies/internal/stripe"
	"github.com/qsweber/lunch-buddies/internal/workflows"
)

func main() {
	deps, err := workflows.NewDepsFromEnv(context.Background())
	if err != nil {
		log.Fatalf("failed to initialize: %v", err)
	}
	inv := invoice.Deps{Repositories: deps.Repositories, Stripe: stripe.New(os.Getenv("STRIPE_API_KEY")), Now: time.Now}
	lambda.Start(inv.Run)
}
