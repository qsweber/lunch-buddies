package repositories

import (
	"context"
	"errors"

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
	BotAccessToken string `dynamodbav:"bot_access_token"`
	Name           string `dynamodbav:"name"`
	CreatedAt      int64  `dynamodbav:"created_at"`
}

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
