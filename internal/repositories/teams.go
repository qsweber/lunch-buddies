package repositories

import (
	"context"
	"errors"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
)

const (
	teamPartitionKeyPrefix = "TEAM#"
	TeamSortKey            = "TEAM"
)

type Team struct {
	PK     string `dynamodbav:"pk"`
	SK     string `dynamodbav:"sk"`
	TeamID string `dynamodbav:"team_id"`
	// BotAccessToken is stored in plaintext, as in the Python app. Encrypting it (e.g. with
	// KMS) is deferred; see the design doc §12.
	BotAccessToken string `dynamodbav:"bot_access_token,omitempty"`
	Name           string `dynamodbav:"name"`
	// CreatedAt is the first install; UpdatedAt the latest install or reinstall.
	CreatedAt int64 `dynamodbav:"created_at"`
	UpdatedAt int64 `dynamodbav:"updated_at,omitempty"`
	// InstalledByUserID is who last installed the app, the person to contact in Slack.
	InstalledByUserID string `dynamodbav:"installed_by_user_id,omitempty"`
	// BotUserID is the app's bot user in this workspace.
	BotUserID string `dynamodbav:"bot_user_id,omitempty"`
	// Scopes are the bot scopes the current token was granted.
	Scopes              []string `dynamodbav:"scopes,omitempty"`
	EnterpriseID        string   `dynamodbav:"enterprise_id,omitempty"`
	IsEnterpriseInstall bool     `dynamodbav:"is_enterprise_install,omitempty"`
	// UninstalledAt is set when Slack reports the app was uninstalled or its token revoked.
	// The token is deleted then; a reinstall replaces the whole record.
	UninstalledAt int64 `dynamodbav:"uninstalled_at,omitempty"`
}

// Installed reports whether the team currently has the app installed.
func (t Team) Installed() bool { return t.UninstalledAt == 0 && t.BotAccessToken != "" }

func TeamPartitionKey(teamID string) string { return teamPartitionKeyPrefix + teamID }

// WithKeys fills in the key attributes derived from TeamID.
func (t Team) WithKeys() Team {
	t.PK = TeamPartitionKey(t.TeamID)
	t.SK = TeamSortKey
	return t
}

type TeamsRepository interface {
	// GetTeam returns the team, or nil if it isn't installed.
	GetTeam(ctx context.Context, teamID string) (*Team, error)
	// PutTeam creates or replaces the team record.
	PutTeam(ctx context.Context, team Team) error
	// MarkTeamUninstalled records an uninstall and deletes the bot token. A team that isn't
	// in the table is ignored.
	MarkTeamUninstalled(ctx context.Context, teamID string, now time.Time) error
}

type TeamsRepositoryImpl struct {
	tableName string
	client    DynamoDBAPI
}

func NewTeamsRepository(tableName string, client DynamoDBAPI) TeamsRepository {
	return &TeamsRepositoryImpl{tableName: tableName, client: client}
}

func (r *TeamsRepositoryImpl) GetTeam(ctx context.Context, teamID string) (*Team, error) {
	out, err := r.client.GetItem(ctx, &dynamodb.GetItemInput{
		TableName: aws.String(r.tableName),
		Key:       key(TeamPartitionKey(teamID), TeamSortKey),
	})
	if err != nil {
		return nil, err
	}
	if out.Item == nil {
		return nil, nil
	}
	var team Team
	if err := attributevalue.UnmarshalMap(out.Item, &team); err != nil {
		return nil, err
	}
	return &team, nil
}

func (r *TeamsRepositoryImpl) PutTeam(ctx context.Context, team Team) error {
	if team.BotAccessToken == "" {
		return errors.New("PutTeam: BotAccessToken is required")
	}
	av, err := attributevalue.MarshalMap(team.WithKeys())
	if err != nil {
		return err
	}
	_, err = r.client.PutItem(ctx, &dynamodb.PutItemInput{TableName: aws.String(r.tableName), Item: av})
	return err
}

func (r *TeamsRepositoryImpl) MarkTeamUninstalled(ctx context.Context, teamID string, now time.Time) error {
	_, err := r.client.UpdateItem(ctx, &dynamodb.UpdateItemInput{
		TableName:           aws.String(r.tableName),
		Key:                 key(TeamPartitionKey(teamID), TeamSortKey),
		UpdateExpression:    aws.String("SET uninstalled_at = :now, updated_at = :now REMOVE bot_access_token"),
		ConditionExpression: aws.String("attribute_exists(pk)"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":now": n(now.UnixMilli()),
		},
	})
	if isConditionFailed(err) {
		return nil
	}
	return err
}

// queryAll pages through a query, calling fn for every item.
func queryAll(ctx context.Context, client DynamoDBAPI, input *dynamodb.QueryInput, fn func(map[string]types.AttributeValue) error) error {
	for {
		out, err := client.Query(ctx, input)
		if err != nil {
			return err
		}
		for _, item := range out.Items {
			if err := fn(item); err != nil {
				return err
			}
		}
		if len(out.LastEvaluatedKey) == 0 {
			return nil
		}
		input.ExclusiveStartKey = out.LastEvaluatedKey
	}
}
