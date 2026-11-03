package main

import (
	"github.com/aws/aws-cdk-go/awscdk/v2/awslambda"
	"github.com/aws/aws-cdk-go/awscdk/v2/awssqs"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

// Stream filters: the router is only invoked for the two transitions that start workflows
// (design doc §4.3). Everything else (responses, recipients, groups, REQUESTED→OPEN,
// CLOSED→COMPLETE, migrated rows) never reaches the Lambda.
const (
	pollRequestedFilter = `{"eventName":["INSERT"],"dynamodb":{"NewImage":{"sk":{"S":["POLL"]},"state":{"S":["REQUESTED"]}}}}`
	pollClosedFilter    = `{"eventName":["MODIFY"],"dynamodb":{"OldImage":{"state":{"S":["OPEN"]}},"NewImage":{"sk":{"S":["POLL"]},"state":{"S":["CLOSED"]}}}}`
)

type StreamResources struct {
	DeadLetterQueue awssqs.CfnQueue
}

func createStreamResources(scope constructs.Construct, projectStackName string, data *DataResources, wf *WorkflowResources) *StreamResources {
	dlq := awssqs.NewCfnQueue(scope, jsii.String("StreamDeadLetterQueue"), &awssqs.CfnQueueProps{
		QueueName:              jsii.String(projectStackName + "-stream-dlq"),
		MessageRetentionPeriod: jsii.Number(14 * 24 * 60 * 60),
	})

	role := newRole(scope, "StreamRole", projectStackName+"-stream-role", "lambda.amazonaws.com", map[string]map[string]interface{}{
		projectStackName + "-stream-policy": policyDocument(
			logStatement,
			statement([]string{"dynamodb:DescribeStream", "dynamodb:GetRecords", "dynamodb:GetShardIterator", "dynamodb:ListStreams"}, *data.Table.AttrStreamArn()),
			statement([]string{"states:StartExecution"}, *wf.StartPoll.AttrArn(), *wf.ClosePoll.AttrArn()),
			// On-failure destination for records that exhaust their retries.
			statement([]string{"sqs:SendMessage"}, *dlq.AttrArn()),
		),
	})

	router := newFunction(scope, projectStackName, functionProps{
		ID:   "StreamRouter",
		Name: "stream-router",
		Zip:  "dynamostream.zip",
		Role: role,
		Env: map[string]*string{
			"START_POLL_STATE_MACHINE_ARN": wf.StartPoll.AttrArn(),
			"CLOSE_POLL_STATE_MACHINE_ARN": wf.ClosePoll.AttrArn(),
		},
		TimeoutSecs: 30,
	})

	mapping := awslambda.NewCfnEventSourceMapping(scope, jsii.String("StreamMapping"), &awslambda.CfnEventSourceMappingProps{
		EventSourceArn:             data.Table.AttrStreamArn(),
		FunctionName:               router.Ref(),
		StartingPosition:           jsii.String("LATEST"),
		BatchSize:                  jsii.Number(10),
		MaximumRetryAttempts:       jsii.Number(5),
		BisectBatchOnFunctionError: jsii.Bool(true),
		FunctionResponseTypes:      jsii.Strings("ReportBatchItemFailures"),
		DestinationConfig: &awslambda.CfnEventSourceMapping_DestinationConfigProperty{
			OnFailure: &awslambda.CfnEventSourceMapping_OnFailureProperty{Destination: dlq.AttrArn()},
		},
		FilterCriteria: &awslambda.CfnEventSourceMapping_FilterCriteriaProperty{
			Filters: []interface{}{
				&awslambda.CfnEventSourceMapping_FilterProperty{Pattern: jsii.String(pollRequestedFilter)},
				&awslambda.CfnEventSourceMapping_FilterProperty{Pattern: jsii.String(pollClosedFilter)},
			},
		},
	})
	mapping.AddDependency(router)

	return &StreamResources{DeadLetterQueue: dlq}
}
