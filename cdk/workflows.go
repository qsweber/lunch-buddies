package main

import (
	"fmt"
	"os"

	"github.com/aws/aws-cdk-go/awscdk/v2/awsstepfunctions"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

type WorkflowResources struct {
	StartPoll awsstepfunctions.CfnStateMachine
	ClosePoll awsstepfunctions.CfnStateMachine
}

// createWorkflowResources creates the worker Lambda (one function for every Step Functions
// task; the payload's "task" field picks the handler) and the StartPoll/ClosePoll state
// machines. The ASL lives in cdk/statemachines and gets ARNs via substitutions.
func createWorkflowResources(scope constructs.Construct, projectStackName string, data *DataResources) *WorkflowResources {
	workerRole := newRole(scope, "WorkerRole", projectStackName+"-worker-role", "lambda.amazonaws.com", map[string]map[string]interface{}{
		projectStackName + "-worker-policy": policyDocument(
			logStatement,
			statement([]string{
				"dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
				"dynamodb:ConditionCheckItem", "dynamodb:Query",
			}, data.TableArn(), data.TableIndexArn()),
		),
	})

	worker := newFunction(scope, projectStackName, functionProps{
		ID:          "Worker",
		Name:        "worker",
		Zip:         "worker.zip",
		Role:        workerRole,
		Env:         map[string]*string{"RECORDS_TABLE": data.Table.Ref()},
		TimeoutSecs: 60,
	})

	sfnRole := newRole(scope, "StateMachineRole", projectStackName+"-sfn-role", "states.amazonaws.com", map[string]map[string]interface{}{
		projectStackName + "-sfn-policy": policyDocument(
			statement([]string{"lambda:InvokeFunction"}, *worker.AttrArn()),
			// MarkPollComplete is a native DynamoDB task.
			statement([]string{"dynamodb:UpdateItem"}, data.TableArn()),
		),
	})

	substitutions := map[string]*string{
		"WorkerFunctionArn": worker.AttrArn(),
		"TableName":         data.Table.Ref(),
	}
	stateMachine := func(id, name, file string) awsstepfunctions.CfnStateMachine {
		definition, err := os.ReadFile(file)
		if err != nil {
			panic(fmt.Sprintf("reading %s: %v", file, err))
		}
		sm := awsstepfunctions.NewCfnStateMachine(scope, jsii.String(id), &awsstepfunctions.CfnStateMachineProps{
			StateMachineName:        jsii.String(projectStackName + "-" + name),
			StateMachineType:        jsii.String("STANDARD"),
			RoleArn:                 sfnRole.AttrArn(),
			DefinitionString:        jsii.String(string(definition)),
			DefinitionSubstitutions: &substitutions,
		})
		sm.AddDependency(sfnRole)
		return sm
	}

	return &WorkflowResources{
		StartPoll: stateMachine("StartPollStateMachine", "start-poll", "statemachines/start_poll.asl.json"),
		ClosePoll: stateMachine("ClosePollStateMachine", "close-poll", "statemachines/close_poll.asl.json"),
	}
}
