// Package params loads the API's settings from SSM Parameter Store at Lambda cold start.
//
// Reading at runtime (rather than having CloudFormation copy values into env vars at deploy
// time) means a changed parameter takes effect on the next cold start without a redeploy,
// and the values never sit in the Lambda's configuration. Both String and SecureString
// parameters work: they're read WithDecryption.
package params

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/ssm"
)

// Keys the API requires under its prefix, e.g. /lunch-buddies/dev/slack_signing_secret.
const (
	SlackSigningSecret     = "slack_signing_secret"
	SlackVerificationToken = "slack_verification_token"
	SlackClientID          = "slack_client_id"
	SlackClientSecret      = "slack_client_secret"
	// LegacyForwardURL is optional. While set, the API forwards every Slack request to the
	// legacy Zappa API at this base URL (production cutover; design doc §8).
	LegacyForwardURL = "legacy_forward_url"
)

// Required lists every key the API needs.
var Required = []string{SlackSigningSecret, SlackVerificationToken, SlackClientID, SlackClientSecret}

// SSMAPI is the subset of the SSM client used here.
type SSMAPI interface {
	GetParametersByPath(ctx context.Context, params *ssm.GetParametersByPathInput, optFns ...func(*ssm.Options)) (*ssm.GetParametersByPathOutput, error)
}

// Load returns every parameter directly under prefix, keyed by its last path segment. It
// fails if any of the required keys is missing or empty.
func Load(ctx context.Context, client SSMAPI, prefix string, required []string) (map[string]string, error) {
	prefix = strings.TrimRight(prefix, "/")
	values := map[string]string{}
	paginator := ssm.NewGetParametersByPathPaginator(client, &ssm.GetParametersByPathInput{
		Path:           aws.String(prefix),
		WithDecryption: aws.Bool(true),
	})
	for paginator.HasMorePages() {
		page, err := paginator.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("reading SSM parameters under %s: %w", prefix, err)
		}
		for _, p := range page.Parameters {
			name := aws.ToString(p.Name)
			values[name[strings.LastIndex(name, "/")+1:]] = aws.ToString(p.Value)
		}
	}

	var missing []string
	for _, key := range required {
		if values[key] == "" {
			missing = append(missing, prefix+"/"+key)
		}
	}
	if len(missing) > 0 {
		sort.Strings(missing)
		return nil, fmt.Errorf("missing SSM parameters: %s", strings.Join(missing, ", "))
	}
	return values, nil
}
