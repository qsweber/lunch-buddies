package server

import (
	"context"
	"errors"
	"log/slog"

	"github.com/qsweber/lunch-buddies/internal/repositories"
	"github.com/qsweber/lunch-buddies/internal/slack"
)

const (
	welcomeMessage = "Thanks for installing Lunch Buddies! To get started, invite me to any channel and say `@Lunch Buddies create`."
	pricingMessage = "\n\nFor information about pricing, check out https://www.lunchbuddiesapp.com/pricing/"
)

// Auth completes the Slack OAuth install: exchange the code, upsert the team (its bot
// token is encrypted by the repository), sync the Stripe customer and send a welcome DM.
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

	lookupToken := access.AccessToken
	if existing != nil {
		lookupToken = existing.BotAccessToken
	}
	user, err := s.sc.Slack.UserInfo(ctx, lookupToken, access.UserID)
	if err != nil {
		return errorResponse(500, err)
	}

	stripeCustomerID := ""
	if existing == nil || existing.StripeCustomerID == "" {
		customer, err := s.sc.Stripe.CreateCustomer(ctx, user.Name, user.Email, access.TeamName)
		if err != nil {
			return errorResponse(500, err)
		}
		if customer != nil {
			stripeCustomerID = customer.ID
		}
	} else {
		if err := s.sc.Stripe.UpdateCustomer(ctx, existing.StripeCustomerID, user.Name, user.Email, access.TeamName); err != nil {
			return errorResponse(500, err)
		}
		stripeCustomerID = existing.StripeCustomerID
	}

	team := repositories.Team{
		TeamID:                 access.TeamID,
		BotAccessToken:         access.AccessToken,
		Name:                   access.TeamName,
		CreatedAt:              s.sc.Now().UnixMilli(),
		FeatureNotifyInChannel: true,
		StripeCustomerID:       stripeCustomerID,
		InvoicingEnabled:       true,
	}
	if existing != nil {
		team.CreatedAt = existing.CreatedAt
		team.FeatureNotifyInChannel = existing.FeatureNotifyInChannel
		team.InvoicingEnabled = existing.InvoicingEnabled
	}
	if err := s.sc.Repositories.Teams.PutTeam(ctx, team); err != nil {
		return errorResponse(500, err)
	}
	slog.Info("team installed", "team_id", team.TeamID, "team_name", team.Name, "reinstall", existing != nil)

	message := welcomeMessage
	if team.InvoicingEnabled {
		message += pricingMessage
	}
	if _, err := s.sc.Slack.PostMessage(ctx, access.AccessToken, slack.Message{Channel: access.UserID, Text: message, AsUser: true}); err != nil {
		return errorResponse(500, err)
	}

	return redirect(s.sc.Config.RegistrationURL)
}
