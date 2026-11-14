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

	CreatePollHelp = "To initiate the process, invite the Lunch Buddies bot to any channel and " +
		"say `@Lunch Buddies create`. This will send a message to each member of the current channel " +
		"asking if they want to participate." +
		"\n\n" +
		"The default options are: `Yes (12:00)`, and `No`, but you can customize by saying `@Lunch Buddies create 1145, 1230`." +
		"\n\n" +
		"The default group size is 6, but this can be customize by saying `@Lunch Buddies create 1145, 1230 size=4`" +
		"\n\n" +
		"You can also create polls using the legacy `/lunch_buddies_create` slash command. " +
		"Regardless of where this command is invoked, it will poll the members of the `#lunch_buddies` channel. " +
		"\n\n" +
		"It is possible to have multiple polls going at the same time; they are uniquely defined by the channel from which they were created. "

	ClosePollHelp = "Once everyone has answered, go back to the same channel from which the poll was created " +
		"and write `@Lunch Buddies close`. This will randomly group the responders by their answer " +
		"and start a private group message for each group. " +
		"\n\n" +
		"If you created the poll with the slash command `/lunch_buddies_create`, you should close it with the slash command `/lunch_buddies_close`."

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
