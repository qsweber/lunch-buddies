package main

import (
	"github.com/aws/aws-cdk-go/awscdk/v2"
	"github.com/aws/jsii-runtime-go"
)

// EnvConfig holds the per-stack (dev/prod) settings.
type EnvConfig struct {
	Env     string
	Account string
	Region  string

	// Route53 hosted zone that ApiDomainName lives in.
	ZoneID string
	// Custom domain for the HTTP API. The Slack app's request URLs point here, so the
	// infrastructure behind it can change without reconfiguring Slack.
	ApiDomainName string

	// SecretName is the Secrets Manager secret holding this stack's Slack settings as
	// a JSON object; see README "Secrets". It must exist before the first deploy.
	SecretName string

	// AlertEmail, if set, is subscribed to the alarms topic.
	AlertEmail string
}

func main() {
	app := awscdk.NewApp(nil)

	account := "120356305272"
	region := "us-west-2"
	zoneID := "Z07290422T6PHN4TKVNW0" // quinnweber.com, shared with go-template

	NewLunchBuddiesStack(app, "lunch-buddies-dev", EnvConfig{
		Env:           "dev",
		Account:       account,
		Region:        region,
		ZoneID:        zoneID,
		ApiDomainName: "dev-lunch-buddies-api.quinnweber.com",
		SecretName:    "lunch-buddies/dev",
	}, &awscdk.StackProps{
		Env: &awscdk.Environment{Account: jsii.String(account), Region: jsii.String(region)},
	})

	NewLunchBuddiesStack(app, "lunch-buddies-prod", EnvConfig{
		Env:           "prod",
		Account:       account,
		Region:        region,
		ZoneID:        zoneID,
		ApiDomainName: "lunch-buddies-api.quinnweber.com",
		SecretName:    "lunch-buddies/prod",
	}, &awscdk.StackProps{
		Env: &awscdk.Environment{Account: jsii.String(account), Region: jsii.String(region)},
	})

	app.Synth(nil)
}
