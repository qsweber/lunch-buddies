package repositories

import (
	"context"
	"errors"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"

	"github.com/qsweber/lunch-buddies/internal/tokencipher"
)

const (
	teamPartitionKeyPrefix = "TEAM#"
	TeamSortKey            = "TEAM"
	// AllTeamsGSI1PK is the sparse GSI1 partition that lists every team (for invoicing).
	AllTeamsGSI1PK = "TEAMS"
)

type Team struct {
	PK     string `dynamodbav:"pk"`
	SK     string `dynamodbav:"sk"`
	GSI1PK string `dynamodbav:"gsi1pk"`
	GSI1SK string `dynamodbav:"gsi1sk"`
	TeamID string `dynamodbav:"team_id"`
	// BotAccessToken is never stored in plaintext: PutTeam encrypts it into
	// EncryptedBotAccessToken and GetTeam decrypts it back.
	BotAccessToken          string `dynamodbav:"-"`
	EncryptedBotAccessToken string `dynamodbav:"bot_access_token_enc"`
	Name                    string `dynamodbav:"name"`
	CreatedAt               int64  `dynamodbav:"created_at"`
	FeatureNotifyInChannel  bool   `dynamodbav:"feature_notify_in_channel"`
	StripeCustomerID        string `dynamodbav:"stripe_customer_id,omitempty"`
	InvoicingEnabled        bool   `dynamodbav:"invoicing_enabled"`
}

func TeamPartitionKey(teamID string) string { return teamPartitionKeyPrefix + teamID }

// WithKeys fills in the key attributes derived from TeamID.
func (t Team) WithKeys() Team {
	t.PK = TeamPartitionKey(t.TeamID)
	t.SK = TeamSortKey
	t.GSI1PK = AllTeamsGSI1PK
	t.GSI1SK = TeamPartitionKey(t.TeamID)
	return t
}

type TeamsRepository interface {
	// GetTeam returns the team with its bot token decrypted, or nil if it isn't installed.
	GetTeam(ctx context.Context, teamID string) (*Team, error)
	// PutTeam creates or replaces the team record.
	PutTeam(ctx context.Context, team Team) error
	// ListTeams returns every installed team. Bot tokens are NOT decrypted (BotAccessToken is
	// empty); call GetTeam for a team whose token you need.
	ListTeams(ctx context.Context) ([]Team, error)
}

type TeamsRepositoryImpl struct {
	tableName string
	client    DynamoDBAPI
	cipher    tokencipher.Cipher
}

func NewTeamsRepository(tableName string, client DynamoDBAPI, cipher tokencipher.Cipher) TeamsRepository {
	return &TeamsRepositoryImpl{tableName: tableName, client: client, cipher: cipher}
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
	if team.EncryptedBotAccessToken != "" {
		token, err := r.cipher.Decrypt(ctx, team.TeamID, team.EncryptedBotAccessToken)
		if err != nil {
			return nil, fmt.Errorf("decrypting bot token for team %s: %w", team.TeamID, err)
		}
		team.BotAccessToken = token
	}
	return &team, nil
}

func (r *TeamsRepositoryImpl) PutTeam(ctx context.Context, team Team) error {
	if team.BotAccessToken == "" {
		return errors.New("PutTeam: BotAccessToken is required")
	}
	encrypted, err := r.cipher.Encrypt(ctx, team.TeamID, team.BotAccessToken)
	if err != nil {
		return fmt.Errorf("encrypting bot token for team %s: %w", team.TeamID, err)
	}
	team.EncryptedBotAccessToken = encrypted
	av, err := attributevalue.MarshalMap(team.WithKeys())
	if err != nil {
		return err
	}
	_, err = r.client.PutItem(ctx, &dynamodb.PutItemInput{TableName: aws.String(r.tableName), Item: av})
	return err
}

func (r *TeamsRepositoryImpl) ListTeams(ctx context.Context) ([]Team, error) {
	var teams []Team
	err := queryAll(ctx, r.client, &dynamodb.QueryInput{
		TableName:              aws.String(r.tableName),
		IndexName:              aws.String(GSI1Name),
		KeyConditionExpression: aws.String("gsi1pk = :pk"),
		ExpressionAttributeValues: map[string]types.AttributeValue{
			":pk": s(AllTeamsGSI1PK),
		},
	}, func(item map[string]types.AttributeValue) error {
		var t Team
		if err := attributevalue.UnmarshalMap(item, &t); err != nil {
			return err
		}
		teams = append(teams, t)
		return nil
	})
	return teams, err
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
