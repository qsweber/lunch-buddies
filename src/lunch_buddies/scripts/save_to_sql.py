import csv

from lunch_buddies.lib.service_context import service_context


def run() -> None:
    teams = service_context.daos.teams.read(None, None)
    polls = service_context.daos.polls.read(None, None)
    poll_responses = service_context.daos.poll_responses.read(None, None)

    with open(".export/teams.csv", "w", newline="") as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(teams[0]._asdict())  # header
        for team in teams:
            spamwriter.writerow(team._asdict().values())

    with open(".export/polls.csv", "w", newline="") as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(polls[0]._asdict())  # header
        for poll in polls:
            spamwriter.writerow(poll._asdict().values())

    with open(".export/poll_responses.csv", "w", newline="") as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(poll_responses[0]._asdict())  # header
        for poll_response in poll_responses:
            spamwriter.writerow(poll_response._asdict().values())


"""
library(data.table)
teams = data.table(read.csv('~/qsweber/lunch-buddies/.export/teams.csv', stringsAsFactors = F))
polls = data.table(read.csv('~/qsweber/lunch-buddies/.export/polls.csv', stringsAsFactors = F))
poll_responses = data.table(read.csv('~/qsweber/lunch-buddies/.export/poll_responses.csv', stringsAsFactors = F))
merge(
    merge(
        teams[order(created_at),list(name, team_id, team_created_at=created_at)],
        polls[,list(team_id, callback_id, poll_created_at=created_at)],
        by='team_id',
        all.x=T
    ),
    poll_responses[,list(
        count=.N,
        count_yes=nrow(.SD[grepl('yes', response, fixed=T)]),
        count_no=nrow(.SD[grepl('no', response, fixed=T)])
    ), by=list(callback_id)],
    by='callback_id',
    all.x=T
)[order(team_created_at, poll_created_at)]
"""
