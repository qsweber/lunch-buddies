package polls

import (
	"fmt"
	"sort"
	"strings"
)

// DefaultChannelName is the channel polled when a poll is created via the slash command.
const DefaultChannelName = "lunch_buddies"

const (
	TagLine = "Builds relationships between teammates by coordinating random lunch groups."

	CreatePollHelp = "*Start a poll:* invite `@Lunch Buddies` to a channel and say `@Lunch Buddies create`. " +
		"Everyone in the channel gets a direct message asking if they can make it to lunch today." +
		"\n\n" +
		"The default options are `Yes (12:00)` and `No`. Choose your own times with `@Lunch Buddies create 1145, 1230`." +
		"\n\n" +
		"Groups have 6 people by default. Choose a size from 2 to 6 with `@Lunch Buddies create 1145, 1230 size=4`." +
		"\n\n" +
		"You can also use the `/lunch_buddies_create` slash command, which always polls the `#lunch_buddies` channel (you need to be a member of it)." +
		"\n\n" +
		"Each channel can have its own poll, so several teams can run polls at the same time."

	ClosePollHelp = "*Close the poll:* once everyone has answered, say `@Lunch Buddies close` in the channel where the poll was created. " +
		"Lunch Buddies randomly groups everyone who said yes, by the time they chose, announces each group in the channel, " +
		"and picks one person in each group to choose where to eat." +
		"\n\n" +
		"If you started the poll with `/lunch_buddies_create`, close it with `/lunch_buddies_close`."

	SupportLine = "If you have any questions, comments or concerns, please send an email to support@lunchbuddiesapp.com"

	AppExplanation = "Meet random teammates for lunch\n\n" + CreatePollHelp + "\n\n" + ClosePollHelp + "\n\n" + SupportLine
)

// User-facing messages. Wording is kept identical to the Python implementation.
const (
	MsgOK                    = "ok!"
	MsgActivePollExists      = "There is already an active poll"
	MsgNoPollFound           = "No poll found"
	MsgPollAlreadyClosed     = "The poll you tried to close has already been closed"
	MsgNoPollResponses       = "No poll responses found"
	MsgPollQuestion          = "Are you able to participate in Lunch Buddies today?"
	MsgPollClosedForResponse = ":no_entry_sign: This poll has already closed, so your answer was not recorded."
	MsgMultipleActivePolls   = "There is more than one open poll. Close it from the channel where it was created by saying `@Lunch Buddies close`."
	MsgSomethingWentWrong    = "Sorry, something went wrong while processing your Lunch Buddies poll. Please try again."
	DefaultChannelNotFound   = "Error creating poll. When creating a poll via the slash command \"/lunch_buddies_create\", there must be a channel named \"#lunch_buddies\", " +
		"however that channel could not be found. You can either create a channel named \"#lunch_buddies\" and try again, or create a poll by inviting \"@Lunch Buddies\" to any channel " +
		"and saying \"@Lunch Buddies create\""
	userNotInDefaultChannel = "Error creating poll. To create a poll via the slash command \"/lunch_buddies_create\", you must be a member of <#%s|%s>. " +
		"You can join that channel and try again."
)

// UserNotInDefaultChannel is the error DM when the slash-command user isn't in #lunch_buddies.
func UserNotInDefaultChannel(channelID, channelName string) string {
	return fmt.Sprintf(userNotInDefaultChannel, channelID, channelName)
}

// ResponseReceived is appended to the poll message after a user clicks a button.
func ResponseReceived(choice Choice) string {
	return fmt.Sprintf(":white_check_mark: Your answer of `%s` was received!", choice.DisplayText)
}

// PollAttachments builds the legacy-attachment buttons for the poll DM.
func PollAttachments(callbackID string, choices []Choice) []map[string]any {
	actions := make([]map[string]any, 0, len(choices))
	for _, c := range choices {
		actions = append(actions, map[string]any{
			"name":  "answer",
			"text":  c.DisplayText,
			"type":  "button",
			"value": c.Key,
		})
	}
	return []map[string]any{{
		"fallback":        "Something has gone wrong.",
		"callback_id":     callbackID,
		"color":           "#3AA3E3",
		"attachment_type": "default",
		"actions":         actions,
	}}
}

// InChannelGroupMessage is posted in the poll channel. userIDs must already be sorted.
func InChannelGroupMessage(choice Choice, userIDs []string) string {
	mentions := make([]string, len(userIDs))
	for i, u := range userIDs {
		mentions[i] = fmt.Sprintf("<@%s>", u)
	}
	return fmt.Sprintf("Hey %s!", strings.Join(mentions, ", ")) +
		" This is your group for today." +
		fmt.Sprintf(" You all should meet somewhere at `%s`.", choice.Time)
}

// PickLocationMessage is the threaded follow-up to InChannelGroupMessage.
func PickLocationMessage(userID string) string {
	return fmt.Sprintf("<@%s> should pick the location.", userID)
}

// Intersect returns the sorted intersection of a and b.
func Intersect(a, b []string) []string {
	set := make(map[string]bool, len(a))
	for _, x := range a {
		set[x] = true
	}
	seen := map[string]bool{}
	var out []string
	for _, x := range b {
		if set[x] && !seen[x] {
			out = append(out, x)
			seen[x] = true
		}
	}
	sort.Strings(out)
	return out
}
