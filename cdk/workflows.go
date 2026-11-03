package main

import (
	"fmt"
	"os"

	"github.com/aws/aws-cdk-go/awscdk/v2/awslambda"
	"github.com/aws/aws-cdk-go/awscdk/v2/awsstepfunctions"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

type WorkflowResources struct {
	StartPoll awsstepfunctions.CfnStateMachine
	ClosePoll awsstepfunctions.CfnStateMachine
	Invoice   awslambda.CfnFunction
}

// createWorkflowResources creates the task Lambdas and the StartPoll/ClosePoll state
// machines. The ASL lives in cdk/statemachines and gets Lambda ARNs via substitutions.
func createWorkflowResources(scope constructs.Construct, projectStackName string, cfg EnvConfig, data *DataResources) *WorkflowResources {
	taskRole := newRole(scope, "TaskRole", projectStackName+"-task-role", "lambda.amazonaws.com", map[string]map[string]interface{}{
		projectStackName + "-task-policy": policyDocument(
			logStatement,
			statement([]string{
				"dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
				"dynamodb:ConditionCheckItem", "dynamodb:Query",
			}, data.TableArn(), data.TableIndexArn()),
		),
	})

	env := map[string]*string{
		"RECORDS_TABLE": data.Table.Ref(),
	}
	task := func(id, name, zip string) awslambda.CfnFunction {
		return newFunction(scope, projectStackName, functionProps{ID: id, Name: name, Zip: zip, Role: taskRole, Env: env, TimeoutSecs: 60})
	}
	preparePoll := task("PreparePoll", "prepare-poll", "preparepoll.zip")
	pollUser := task("PollUser", "poll-user", "polluser.zip")
	formGroups := task("FormGroups", "form-groups", "formgroups.zip")
	notifyGroup := task("NotifyGroup", "notify-group", "notifygroup.zip")
	notifyFailure := task("NotifyFailure", "notify-failure", "notifyfailure.zip")

	invoiceEnv := map[string]*string{"STRIPE_API_KEY": secretRef(cfg, "stripe_api_key")}
	for k, v := range env {
		invoiceEnv[k] = v
	}
	invoice := newFunction(scope, projectStackName, functionProps{
		ID: "Invoice", Name: "invoice", Zip: "invoice.zip", Role: taskRole, Env: invoiceEnv, TimeoutSecs: 300,
	})

	tasks := []awslambda.CfnFunction{preparePoll, pollUser, formGroups, notifyGroup, notifyFailure}
	var taskArns []string
	for _, f := range tasks {
		taskArns = append(taskArns, *f.AttrArn())
	}
	sfnRole := newRole(scope, "StateMachineRole", projectStackName+"-sfn-role", "states.amazonaws.com", map[string]map[string]interface{}{
		projectStackName + "-sfn-policy": policyDocument(
			statement([]string{"lambda:InvokeFunction"}, taskArns...),
			// MarkPollComplete is a native DynamoDB task.
			statement([]string{"dynamodb:UpdateItem"}, data.TableArn()),
		),
	})

	substitutions := map[string]*string{
		"PreparePollFunctionArn":   preparePoll.AttrArn(),
		"PollUserFunctionArn":      pollUser.AttrArn(),
		"FormGroupsFunctionArn":    formGroups.AttrArn(),
		"NotifyGroupFunctionArn":   notifyGroup.AttrArn(),
		"NotifyFailureFunctionArn": notifyFailure.AttrArn(),
		"TableName":                data.Table.Ref(),
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
		Invoice:   invoice,
	}
}
