package main

import (
	"fmt"

	"github.com/aws/aws-cdk-go/awscdk/v2"
	"github.com/aws/aws-cdk-go/awscdk/v2/awsiam"
	"github.com/aws/aws-cdk-go/awscdk/v2/awslambda"
	"github.com/aws/aws-cdk-go/awscdk/v2/awslogs"
	"github.com/aws/aws-cdk-go/awscdk/v2/awss3assets"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

// lambdaRuntime: provided.al2 (the template's choice) reached end of support with Amazon
// Linux 2 in mid-2026; Go binaries run unchanged on al2023.
const lambdaRuntime = "provided.al2023"

const logRetentionDays = 90

type functionProps struct {
	ID          string // construct id prefix, e.g. "PollUser"
	Name        string // short name; the function is "<stack>-<name>"
	Zip         string // under ../dist
	Role        awsiam.CfnRole
	Env         map[string]*string
	TimeoutSecs float64
	// ReservedConcurrency caps instances; 0 leaves it unset.
	ReservedConcurrency float64
}

// newFunction creates a Go Lambda from dist/<zip> plus an explicit log group, so logs have a
// retention period instead of the default "never expire".
func newFunction(scope constructs.Construct, projectStackName string, p functionProps) awslambda.CfnFunction {
	name := projectStackName + "-" + p.Name

	logGroup := awslogs.NewCfnLogGroup(scope, jsii.String(p.ID+"LogGroup"), &awslogs.CfnLogGroupProps{
		LogGroupName:    jsii.String("/aws/lambda/" + name),
		RetentionInDays: jsii.Number(logRetentionDays),
	})
	logGroup.ApplyRemovalPolicy(awscdk.RemovalPolicy_DESTROY, nil)

	asset := awss3assets.NewAsset(scope, jsii.String(p.ID+"FunctionAsset"), &awss3assets.AssetProps{
		Path: jsii.String(fmt.Sprintf("../dist/%s", p.Zip)),
	})

	props := &awslambda.CfnFunctionProps{
		FunctionName:  jsii.String(name),
		Handler:       jsii.String("bootstrap"),
		Role:          p.Role.AttrArn(),
		Runtime:       jsii.String(lambdaRuntime),
		Architectures: jsii.Strings("x86_64"),
		MemorySize:    jsii.Number(256),
		Timeout:       jsii.Number(p.TimeoutSecs),
		Code: &awslambda.CfnFunction_CodeProperty{
			S3Bucket: asset.S3BucketName(),
			S3Key:    asset.S3ObjectKey(),
		},
		Environment: &awslambda.CfnFunction_EnvironmentProperty{Variables: p.Env},
	}
	if p.ReservedConcurrency > 0 {
		props.ReservedConcurrentExecutions = jsii.Number(p.ReservedConcurrency)
	}
	fn := awslambda.NewCfnFunction(scope, jsii.String(p.ID+"Function"), props)
	fn.AddDependency(p.Role)
	fn.AddDependency(logGroup)
	return fn
}

// secretRef is a CloudFormation dynamic reference to one key of the stack's secret. The
// value is resolved at deploy time into the function's environment.
func secretRef(cfg EnvConfig, key string) *string {
	return jsii.String(fmt.Sprintf("{{resolve:secretsmanager:%s:SecretString:%s}}", cfg.SecretName, key))
}
