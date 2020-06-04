import logging

from lunch_buddies.constants.polls import DEFAULT_GROUP_SIZE
from lunch_buddies.dao.polls import PollsDao

logger = logging.getLogger(__name__)


def migrate():
    polls_dao = PollsDao()
    raw_polls = polls_dao._read_internal(None, None)
    dynamo_table = polls_dao._get_dynamo_table()

    for raw_poll in raw_polls:
        if "group_size" in raw_poll:
            continue

        team_id = raw_poll["team_id"]

        dynamo_table.update_item(
            Key={"team_id": team_id, "created_at": raw_poll["created_at"]},
            AttributeUpdates={
                "group_size": {"Value": DEFAULT_GROUP_SIZE, "Action": "PUT"}
            },
        )
