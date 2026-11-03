package main

import (
	"github.com/aws/aws-cdk-go/awscdk/v2/awsapigatewayv2"
	"github.com/aws/aws-cdk-go/awscdk/v2/awscertificatemanager"
	"github.com/aws/aws-cdk-go/awscdk/v2/awsroute53"
	"github.com/aws/constructs-go/constructs/v10"
	"github.com/aws/jsii-runtime-go"
)

// createCustomDomainResources serves the HTTP API at cfg.ApiDomainName through a regional
// custom domain, with its own ACM certificate in the stack's region. CloudFormation creates the
// certificate's DNS validation record in the hosted zone and waits for it to be issued.
func createCustomDomainResources(scope constructs.Construct, cfg EnvConfig, api awsapigatewayv2.CfnApi, stage awsapigatewayv2.CfnStage) {
	certificate := awscertificatemanager.NewCfnCertificate(scope, jsii.String("ApiCertificate"), &awscertificatemanager.CfnCertificateProps{
		DomainName:       jsii.String(cfg.ApiDomainName),
		ValidationMethod: jsii.String("DNS"),
		DomainValidationOptions: []interface{}{
			&awscertificatemanager.CfnCertificate_DomainValidationOptionProperty{
				DomainName:   jsii.String(cfg.ApiDomainName),
				HostedZoneId: jsii.String(cfg.ZoneID),
			},
		},
	})

	domainName := awsapigatewayv2.NewCfnDomainName(scope, jsii.String("ApiRegionalDomainName"), &awsapigatewayv2.CfnDomainNameProps{
		DomainName: jsii.String(cfg.ApiDomainName),
		DomainNameConfigurations: []interface{}{
			&awsapigatewayv2.CfnDomainName_DomainNameConfigurationProperty{
				CertificateArn: certificate.Ref(),
				EndpointType:   jsii.String("REGIONAL"),
				SecurityPolicy: jsii.String("TLS_1_2"),
			},
		},
	})

	// Map the domain root to the $default stage. Referencing the stage (rather than the literal
	// "$default") makes the mapping wait for the stage to exist.
	awsapigatewayv2.NewCfnApiMapping(scope, jsii.String("ApiMapping"), &awsapigatewayv2.CfnApiMappingProps{
		ApiId:      api.Ref(),
		DomainName: domainName.Ref(),
		Stage:      stage.Ref(),
	})

	awsroute53.NewCfnRecordSet(scope, jsii.String("ApiRegionalDomainAliasRecord"), &awsroute53.CfnRecordSetProps{
		Name:         jsii.String(cfg.ApiDomainName),
		Type:         jsii.String("A"),
		HostedZoneId: jsii.String(cfg.ZoneID),
		AliasTarget: &awsroute53.CfnRecordSet_AliasTargetProperty{
			DnsName:      domainName.AttrRegionalDomainName(),
			HostedZoneId: domainName.AttrRegionalHostedZoneId(),
		},
	})
}
