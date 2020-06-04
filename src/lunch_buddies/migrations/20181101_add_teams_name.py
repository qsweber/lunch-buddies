import logging

from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.teams import TeamsDao

logger = logging.getLogger(__name__)


def migrate():
    slack_client = SlackClient()
    teams_dao = TeamsDao()
    teams = teams_dao.read()
    dynamo_table = teams_dao._get_dynamo_table()

    for team in teams:
        if team.name:
            logger.info("already exists for {}".format(team.name))
            continue

        team_info = slack_client._get_base_client_for_team(
            team.bot_access_token
        ).api_call("team.info")

        if not team_info["ok"]:
            logger.info("issue for {}".format(team.team_id))
            continue

        dynamo_table.update_item(
            Key={"team_id": team.team_id},
            AttributeUpdates={
                "name": {"Value": team_info["team"]["name"], "Action": "PUT"}
            },
        )
