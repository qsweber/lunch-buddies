// Command worker is the single Lambda behind every Step Functions task. The state machines
// name the task in the payload's "task" field; see workflows.Deps.Handle.
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
	lambda.Start(deps.Handle)
}
