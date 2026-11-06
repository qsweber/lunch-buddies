package main

import (
	"fmt"

	"github.com/aws/aws-cdk-go/awscdk/v2"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

func NewLunchBuddiesStack(scope constructs.Construct, id string, cfg EnvConfig, props *awscdk.StackProps) awscdk.Stack {
	stack := awscdk.NewStack(scope, jsii.String(id), props)
	projectStackName := "lunch-buddies-" + cfg.Env

	data := createDataResources(stack, projectStackName, cfg)
	workflows := createWorkflowResources(stack, projectStackName, data)
	stream := createStreamResources(stack, projectStackName, data, workflows)
	createAlarms(stack, projectStackName, cfg, workflows, stream)
	api := createAPIGatewayResources(stack, projectStackName, cfg, data)
	createCustomDomainResources(stack, cfg, api.Api, api.Stage)

	output := func(name string, value *string) {
		awscdk.NewCfnOutput(stack, jsii.String("Output"+name), &awscdk.CfnOutputProps{Value: value})
	}
	output("RecordsTable", data.Table.Ref())
	output("InvocationURL", jsii.String(fmt.Sprintf("https://%s.execute-api.%s.amazonaws.com", *api.Api.Ref(), cfg.Region)))
	output("CustomDomainURL", jsii.String(fmt.Sprintf("https://%s", cfg.ApiDomainName)))

	return stack
}
