package main

import (
	"github.com/aws/aws-cdk-go/awscdk/v2/awscloudwatch"
	"github.com/aws/aws-cdk-go/awscdk/v2/awsevents"
	"github.com/aws/aws-cdk-go/awscdk/v2/awssns"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

// createAlarms sends to one SNS topic when a workflow execution fails or a stream record
// lands in the dead-letter queue.
func createAlarms(scope constructs.Construct, projectStackName string, cfg EnvConfig, wf *WorkflowResources, stream *StreamResources) awssns.CfnTopic {
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

	return topic
}
