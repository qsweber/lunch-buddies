package main

import (
	"fmt"

	"github.com/aws/aws-cdk-go/awscdk/v2/awsapigatewayv2"
	"github.com/aws/aws-cdk-go/awscdk/v2/awslambda"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

// Burst protection, as in go-template. Slack traffic for this app is tiny.
const (
	apiThrottlingRateLimit  = 50
	apiThrottlingBurstLimit = 100
	apiReservedConcurrency  = 20
)

type APIGatewayResources struct {
	Function awslambda.CfnFunction
	Api      awsapigatewayv2.CfnApi
	Stage    awsapigatewayv2.CfnStage
}

func createAPIGatewayResources(scope constructs.Construct, projectStackName string, cfg EnvConfig, data *DataResources) *APIGatewayResources {
	role := newRole(scope, "ApiRole", projectStackName+"-api-role", "lambda.amazonaws.com", map[string]map[string]interface{}{
		projectStackName + "-api-policy": policyDocument(
			logStatement,
			statement([]string{
				"dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem",
				"dynamodb:ConditionCheckItem", "dynamodb:Query",
			}, data.TableArn()),
			// Slack settings are read at cold start (internal/params). SecureString values use
			// the AWS-managed aws/ssm key, whose key policy already allows decryption via SSM.
			statement([]string{"ssm:GetParametersByPath"}, parameterPathArn(cfg)),
		),
	})

	function := newFunction(scope, projectStackName, functionProps{
		ID:   "Api",
		Name: "api",
		Zip:  "apigateway.zip",
		Role: role,
		Env: map[string]*string{
			"RECORDS_TABLE":    data.Table.Ref(),
			"PARAMETER_PREFIX": jsii.String(cfg.ParameterPrefix),
			// Public base URL; the OAuth install URL and redirect URI are built from it.
			"API_BASE_URL": jsii.String("https://" + cfg.ApiDomainName),
		},
		TimeoutSecs:         15,
		ReservedConcurrency: apiReservedConcurrency,
	})

	// An HTTP API with a single catch-all route: routing and auth happen in the Go handler.
	api := awsapigatewayv2.NewCfnApi(scope, jsii.String("HttpApi"), &awsapigatewayv2.CfnApiProps{
		Name:         jsii.String(projectStackName + "-api"),
		ProtocolType: jsii.String("HTTP"),
	})
	integration := awsapigatewayv2.NewCfnIntegration(scope, jsii.String("HttpApiIntegration"), &awsapigatewayv2.CfnIntegrationProps{
		ApiId:                api.Ref(),
		IntegrationType:      jsii.String("AWS_PROXY"),
		IntegrationUri:       function.AttrArn(),
		PayloadFormatVersion: jsii.String("2.0"),
	})
	route := awsapigatewayv2.NewCfnRoute(scope, jsii.String("HttpApiDefaultRoute"), &awsapigatewayv2.CfnRouteProps{
		ApiId:    api.Ref(),
		RouteKey: jsii.String("$default"),
		Target:   jsii.String(fmt.Sprintf("integrations/%s", *integration.Ref())),
	})
	stage := awsapigatewayv2.NewCfnStage(scope, jsii.String("HttpApiStage"), &awsapigatewayv2.CfnStageProps{
		ApiId:      api.Ref(),
		StageName:  jsii.String("$default"),
		AutoDeploy: jsii.Bool(true),
		DefaultRouteSettings: &awsapigatewayv2.CfnStage_RouteSettingsProperty{
			ThrottlingRateLimit:  jsii.Number(apiThrottlingRateLimit),
			ThrottlingBurstLimit: jsii.Number(apiThrottlingBurstLimit),
		},
	})
	stage.AddDependency(route)

	awslambda.NewCfnPermission(scope, jsii.String("APIPermission"), &awslambda.CfnPermissionProps{
		Action:       jsii.String("lambda:InvokeFunction"),
		FunctionName: function.Ref(),
		Principal:    jsii.String("apigateway.amazonaws.com"),
		SourceArn:    jsii.String(fmt.Sprintf("arn:aws:execute-api:%s:%s:%s/*", cfg.Region, cfg.Account, *api.Ref())),
	})

	return &APIGatewayResources{Function: function, Api: api, Stage: stage}
}
