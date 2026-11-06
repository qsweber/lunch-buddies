package server

import (
	"context"
	"errors"
	"log/slog"

	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/slack"
)

const welcomeMessage = "Thanks for installing Lunch Buddies! To get started, invite me to any channel and say `@Lunch Buddies create`."

// Auth completes the Slack OAuth install: exchange the code, upsert the team and send a
// welcome DM.
//
// Unlike the Python app, this never logs the OAuth response, which contains the bot token.
func (s *ServerImpl) Auth(ctx context.Context, req Request) Response {
	code := req.QueryParams["code"]
	if code == "" {
		return errorResponse(400, errors.New("missing code"))
	}

	access, err := s.sc.Slack.OAuthV2Access(ctx, s.sc.Config.ClientID, s.sc.Config.ClientSecret, code)
	if err != nil {
		return errorResponse(500, err)
	}

	existing, err := s.sc.Repositories.Teams.GetTeam(ctx, access.TeamID)
	if err != nil {
		return errorResponse(500, err)
	}

	team := repositories.Team{
		TeamID:                 access.TeamID,
		BotAccessToken:         access.AccessToken,
		Name:                   access.TeamName,
		CreatedAt:              s.sc.Now().UnixMilli(),
		FeatureNotifyInChannel: true,
	}
	if existing != nil {
		team.CreatedAt = existing.CreatedAt
		team.FeatureNotifyInChannel = existing.FeatureNotifyInChannel
	}
	if err := s.sc.Repositories.Teams.PutTeam(ctx, team); err != nil {
		return errorResponse(500, err)
	}
	slog.Info("team installed", "team_id", team.TeamID, "team_name", team.Name, "reinstall", existing != nil)

	if _, err := s.sc.Slack.PostMessage(ctx, access.AccessToken, slack.Message{Channel: access.UserID, Text: welcomeMessage, AsUser: true}); err != nil {
		return errorResponse(500, err)
	}

	return redirect(s.sc.Config.RegistrationURL)
}
