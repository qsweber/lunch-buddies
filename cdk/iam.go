package main

import (
	"github.com/aws/aws-cdk-go/awscdk/v2/awsiam"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

func assumeRolePolicy(service string) map[string]interface{} {
	return map[string]interface{}{
		"Version": "2012-10-17",
		"Statement": []interface{}{
			map[string]interface{}{
				"Effect":    "Allow",
				"Principal": map[string]interface{}{"Service": service},
				"Action":    "sts:AssumeRole",
			},
		},
	}
}

func statement(actions []string, resources ...string) map[string]interface{} {
	a := make([]interface{}, len(actions))
	for i, v := range actions {
		a[i] = v
	}
	r := make([]interface{}, len(resources))
	for i, v := range resources {
		r[i] = v
	}
	return map[string]interface{}{"Effect": "Allow", "Action": a, "Resource": r}
}

func policyDocument(statements ...map[string]interface{}) map[string]interface{} {
	s := make([]interface{}, len(statements))
	for i, v := range statements {
		s[i] = v
	}
	return map[string]interface{}{"Version": "2012-10-17", "Statement": s}
}

var logStatement = statement([]string{"logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"}, "arn:aws:logs:*:*:*")

// newRole builds a role with inline policies (template style: CfnRole with Policies, no
// separate policy resources).
func newRole(scope constructs.Construct, id, name, service string, policies map[string]map[string]interface{}) awsiam.CfnRole {
	var inline []interface{}
	for policyName, doc := range policies {
		inline = append(inline, &awsiam.CfnRole_PolicyProperty{
			PolicyName:     jsii.String(policyName),
			PolicyDocument: doc,
		})
	}
	return awsiam.NewCfnRole(scope, jsii.String(id), &awsiam.CfnRoleProps{
		RoleName:                 jsii.String(name),
		AssumeRolePolicyDocument: assumeRolePolicy(service),
		Policies:                 inline,
	})
}
