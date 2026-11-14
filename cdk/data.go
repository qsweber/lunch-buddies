package main

import (
	"github.com/aws/aws-cdk-go/awscdk/v2"
	"github.com/aws/aws-cdk-go/awscdk/v2/awsdynamodb"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

type DataResources struct {
	Table awsdynamodb.CfnTable
}

func (d *DataResources) TableArn() string { return *d.Table.AttrArn() }

// createDataResources creates the single records table.
func createDataResources(scope constructs.Construct, projectStackName string, cfg EnvConfig) *DataResources {
	str := func(name string) *awsdynamodb.CfnTable_AttributeDefinitionProperty {
		return &awsdynamodb.CfnTable_AttributeDefinitionProperty{AttributeName: jsii.String(name), AttributeType: jsii.String("S")}
	}
	keySchema := func(hash, rng string) []interface{} {
		return []interface{}{
			&awsdynamodb.CfnTable_KeySchemaProperty{AttributeName: jsii.String(hash), KeyType: jsii.String("HASH")},
			&awsdynamodb.CfnTable_KeySchemaProperty{AttributeName: jsii.String(rng), KeyType: jsii.String("RANGE")},
		}
	}

	table := awsdynamodb.NewCfnTable(scope, jsii.String("RecordsTable"), &awsdynamodb.CfnTableProps{
		TableName:            jsii.String(projectStackName + "-records"),
		BillingMode:          jsii.String("PAY_PER_REQUEST"),
		KeySchema:            keySchema("pk", "sk"),
		AttributeDefinitions: []interface{}{str("pk"), str("sk")},
		// NEW_AND_OLD_IMAGES (not the template's NEW_IMAGE): the close transition is detected
		// from OldImage.state = OPEN.
		StreamSpecification: &awsdynamodb.CfnTable_StreamSpecificationProperty{
			StreamViewType: jsii.String("NEW_AND_OLD_IMAGES"),
		},
		PointInTimeRecoverySpecification: &awsdynamodb.CfnTable_PointInTimeRecoverySpecificationProperty{
			PointInTimeRecoveryEnabled: jsii.Bool(true),
		},
		DeletionProtectionEnabled: jsii.Bool(cfg.Env == "prod"),
	})
	table.ApplyRemovalPolicy(awscdk.RemovalPolicy_RETAIN, nil)

	return &DataResources{Table: table}
}
