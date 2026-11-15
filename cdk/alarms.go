package main

import (
	"github.com/aws/aws-cdk-go/awscdk/v2/awscloudwatch"
	"github.com/aws/aws-cdk-go/awscdk/v2/awsevents"
	"github.com/aws/aws-cdk-go/awscdk/v2/awslogs"
	"github.com/aws/aws-cdk-go/awscdk/v2/awssns"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

// errorLogPattern matches the level slog's default handler writes for slog.Error ("... ERROR
// msg key=value") and Go's panic output. It is a CloudWatch Logs filter pattern: any term.
const errorLogPattern = "?ERROR ?panic"

// createAlarms sends to one SNS topic when a workflow execution fails, a stream record lands
// in the dead-letter queue, any Lambda logs an error, or the API Lambda itself fails.
func createAlarms(scope constructs.Construct, projectStackName string, cfg EnvConfig, wf *WorkflowResources, stream *StreamResources, api *APIGatewayResources) awssns.CfnTopic {
	topic := awssns.NewCfnTopic(scope, jsii.String("AlarmsTopic"), &awssns.CfnTopicProps{
		TopicName: jsii.String(projectStackName + "-alarms"),
	})
	if cfg.AlertEmail != "" {
		awssns.NewCfnSubscription(scope, jsii.String("AlarmsEmail"), &awssns.CfnSubscriptionProps{
			TopicArn: topic.Ref(),
			Protocol: jsii.String("email"),
			Endpoint: jsii.String(cfg.AlertEmail),
		})
	}

	awssns.NewCfnTopicPolicy(scope, jsii.String("AlarmsTopicPolicy"), &awssns.CfnTopicPolicyProps{
		Topics: jsii.Strings(*topic.Ref()),
		PolicyDocument: policyDocument(map[string]interface{}{
			"Effect":    "Allow",
			"Principal": map[string]interface{}{"Service": []interface{}{"events.amazonaws.com", "cloudwatch.amazonaws.com"}},
			"Action":    "sns:Publish",
			"Resource":  *topic.Ref(),
		}),
	})

	awsevents.NewCfnRule(scope, jsii.String("WorkflowFailedRule"), &awsevents.CfnRuleProps{
		Name: jsii.String(projectStackName + "-workflow-failed"),
		EventPattern: map[string]interface{}{
			"source":      []interface{}{"aws.states"},
			"detail-type": []interface{}{"Step Functions Execution Status Change"},
			"detail": map[string]interface{}{
				"status":          []interface{}{"FAILED", "TIMED_OUT", "ABORTED"},
				"stateMachineArn": []interface{}{*wf.StartPoll.AttrArn(), *wf.ClosePoll.AttrArn()},
			},
		},
		Targets: []interface{}{
			&awsevents.CfnRule_TargetProperty{Id: jsii.String("alarms"), Arn: topic.Ref()},
		},
	})

	awscloudwatch.NewCfnAlarm(scope, jsii.String("StreamDLQAlarm"), &awscloudwatch.CfnAlarmProps{
		AlarmName:          jsii.String(projectStackName + "-stream-dlq-not-empty"),
		Namespace:          jsii.String("AWS/SQS"),
		MetricName:         jsii.String("ApproximateNumberOfMessagesVisible"),
		Dimensions:         []interface{}{&awscloudwatch.CfnAlarm_DimensionProperty{Name: jsii.String("QueueName"), Value: stream.DeadLetterQueue.AttrQueueName()}},
		Statistic:          jsii.String("Maximum"),
		Period:             jsii.Number(300),
		EvaluationPeriods:  jsii.Number(1),
		Threshold:          jsii.Number(0),
		ComparisonOperator: jsii.String("GreaterThanThreshold"),
		TreatMissingData:   jsii.String("notBreaching"),
		AlarmActions:       &[]interface{}{topic.Ref()},
	})

	// The API handler turns errors into a 5xx response and logs them, so the invocation still
	// succeeds and no other alarm sees it. The worker and stream router also log errors they
	// handle (e.g. a failed DM) without failing. One metric and alarm per log group.
	for _, fn := range []*lambdaFunction{api.Function, wf.Worker, stream.Router} {
		metricName := fn.Name + "-logged-errors"
		filter := awslogs.NewCfnMetricFilter(scope, jsii.String(fn.ID+"ErrorLogMetricFilter"), &awslogs.CfnMetricFilterProps{
			LogGroupName:  fn.LogGroup.Ref(),
			FilterPattern: jsii.String(errorLogPattern),
			MetricTransformations: []interface{}{&awslogs.CfnMetricFilter_MetricTransformationProperty{
				MetricNamespace: jsii.String(logMetricNamespace),
				MetricName:      jsii.String(metricName),
				MetricValue:     jsii.String("1"),
			}},
		})
		filter.AddDependency(fn.LogGroup)

		awscloudwatch.NewCfnAlarm(scope, jsii.String(fn.ID+"ErrorLogAlarm"), &awscloudwatch.CfnAlarmProps{
			AlarmName:          jsii.String(fn.Name + "-errors-logged"),
			AlarmDescription:   jsii.String("Error lines in " + *fn.LogGroup.LogGroupName()),
			Namespace:          jsii.String(logMetricNamespace),
			MetricName:         jsii.String(metricName),
			Statistic:          jsii.String("Sum"),
			Period:             jsii.Number(300),
			EvaluationPeriods:  jsii.Number(1),
			Threshold:          jsii.Number(0),
			ComparisonOperator: jsii.String("GreaterThanThreshold"),
			TreatMissingData:   jsii.String("notBreaching"),
			AlarmActions:       &[]interface{}{topic.Ref()},
		})
	}

	// Backstop for failures that never reach a log line: timeouts, crashes, init errors.
	// The worker and stream router are covered by the workflow-failed rule and the DLQ.
	awscloudwatch.NewCfnAlarm(scope, jsii.String("ApiFunctionErrorsAlarm"), &awscloudwatch.CfnAlarmProps{
		AlarmName:          jsii.String(api.Function.Name + "-invocation-errors"),
		Namespace:          jsii.String("AWS/Lambda"),
		MetricName:         jsii.String("Errors"),
		Dimensions:         []interface{}{&awscloudwatch.CfnAlarm_DimensionProperty{Name: jsii.String("FunctionName"), Value: api.Function.Function.Ref()}},
		Statistic:          jsii.String("Sum"),
		Period:             jsii.Number(300),
		EvaluationPeriods:  jsii.Number(1),
		Threshold:          jsii.Number(0),
		ComparisonOperator: jsii.String("GreaterThanThreshold"),
		TreatMissingData:   jsii.String("notBreaching"),
		AlarmActions:       &[]interface{}{topic.Ref()},
	})

	return topic
}

// logMetricNamespace holds the metrics made from log filters.
const logMetricNamespace = "LunchBuddies"
