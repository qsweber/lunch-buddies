// Command notifyfailure is the Step Functions task Lambda for workflows.Deps.NotifyFailure.
package main

import (
	"context"
	"log"

	"github.com/aws/aws-lambda-go/lambda"

	"github.com/qsweber/lunch-buddies/internal/workflows"
)

func main() {
	deps, err := workflows.NewDepsFromEnv(context.Background())
	if err != nil {
		log.Fatalf("failed to initialize: %v", err)
	}
	lambda.Start(deps.NotifyFailure)
}
