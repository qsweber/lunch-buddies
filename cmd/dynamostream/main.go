// Command dynamostream is the DynamoDB stream consumer. It starts the StartPoll and
// ClosePoll state machines on poll state transitions (see workflows.Router).
package main

import (
	"context"
	"log"
	"os"

	"github.com/aws/aws-lambda-go/lambda"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/sfn"

	"github.com/qsweber/lunch-buddies/internal/workflows"
)

func main() {
	cfg, err := awsconfig.LoadDefaultConfig(context.Background())
	if err != nil {
		log.Fatalf("failed to load AWS config: %v", err)
	}
	router := workflows.Router{
		SFN:                   sfn.NewFromConfig(cfg),
		StartPollStateMachine: os.Getenv("START_POLL_STATE_MACHINE_ARN"),
		ClosePollStateMachine: os.Getenv("CLOSE_POLL_STATE_MACHINE_ARN"),
	}
	if router.StartPollStateMachine == "" || router.ClosePollStateMachine == "" {
		log.Fatal("START_POLL_STATE_MACHINE_ARN and CLOSE_POLL_STATE_MACHINE_ARN must be set")
	}
	lambda.Start(router.Handle)
}
