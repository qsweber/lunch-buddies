package server

import (
	"context"
	"errors"
	"log/slog"
	"net/url"
	"strings"

	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/slack"
)

// BotScopes are the OAuth scopes requested on install. They must match the scopes configured
// in the Slack app (OAuth & Permissions → Bot Token Scopes); Slack reviews any change.
var BotScopes = []string{
	"app_mentions:read", // @Lunch Buddies create / close / summary / help
	"channels:read",     // members of public channels to poll; finding #lunch_buddies
	"chat:write",        // poll DMs, group announcements, replies
	"commands",          // /lunch_buddies_create, /lunch_buddies_close
	"groups:read",       // members of private channels the app was invited to
	"im:history",        // commands sent to the bot by DM (message.im events)
	"users:read",        // the requester's time zone for summary dates
}

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

	access, err := s.sc.Slack.OAuthV2Access(ctx, s.sc.Config.ClientID, s.sc.Config.ClientSecret, code, s.redirectURI())
	if err != nil {
		return errorResponse(500, err)
	}

	existing, err := s.sc.Repositories.Teams.GetTeam(ctx, access.TeamID)
	if err != nil {
		return errorResponse(500, err)
	}

	now := s.sc.Now().UnixMilli()
	team := repositories.Team{
		TeamID:              access.TeamID,
		BotAccessToken:      access.AccessToken,
		Name:                access.TeamName,
		CreatedAt:           now,
		UpdatedAt:           now,
		InstalledByUserID:   access.UserID,
		BotUserID:           access.BotUserID,
		Scopes:              access.Scopes,
		EnterpriseID:        access.EnterpriseID,
		IsEnterpriseInstall: access.IsEnterpriseInstall,
	}
	if existing != nil {
		team.CreatedAt = existing.CreatedAt
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

// redirectURI is where Slack sends the browser back after install. It must be listed under
// the Slack app's OAuth & Permissions → Redirect URLs.
func (s *ServerImpl) redirectURI() string {
	return s.sc.Config.APIBaseURL + PathAuth
}

// Install redirects to Slack's "Add to Slack" authorize page for this app.
func (s *ServerImpl) Install() Response {
	if s.sc.Config.APIBaseURL == "" || s.sc.Config.ClientID == "" {
		return errorResponse(500, errors.New("install is not configured (API_BASE_URL and slack_client_id are required)"))
	}
	query := url.Values{
		"client_id":    {s.sc.Config.ClientID},
		"scope":        {strings.Join(BotScopes, ",")},
		"redirect_uri": {s.redirectURI()},
	}
	return redirect("https://slack.com/oauth/v2/authorize?" + query.Encode())
}
