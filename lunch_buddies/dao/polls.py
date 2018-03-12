from decimal import Decimal
import json

from lunch_buddies.constants.polls import CLOSED
from lunch_buddies.dao.base import Dao
from lunch_buddies.models.polls import Poll, ChoiceList, Choice


class PollsDao(Dao):
    def __init__(self):
        super(PollsDao, self).__init__(Poll)

    def _as_dynamo_object_hook(self, field, value):
        if field == 'choices':
            return json.dumps([
                choice._asdict()
                for choice in value
            ])

        raise Exception('should not get this far')

    def _as_model_hook(self, field, value):
        if field == 'choices':
            return ChoiceList([
                Choice(
                    key=str(choice['key']),
                    is_yes=bool(choice['is_yes']),
                    time=choice['time'],
                    display_text=str(choice['display_text']),
                )
                for choice in json.loads(value)
            ])

        raise Exception('should not get this far')

    def find_by_callback_id(self, team_id, callback_id):
        polls = [
            poll
            for poll in self.read('team_id', team_id)
            if poll.callback_id == callback_id
        ]

        if len(polls) == 0:
            return None
        elif len(polls) > 1:
            raise Exception('more than one poll found')

        return polls[0]

    def find_latest_by_team_id(self, team_id):
        polls = self.read('team_id', team_id)
        if polls:
            return polls[-1]
        else:
            return None

    def mark_poll_closed(self, poll):
        dynamo_table = self._get_dynamo_table()

        return dynamo_table.update_item(
            Key={
                'team_id': poll.team_id,
                'created_at': Decimal(poll.created_at.timestamp()),
            },
            AttributeUpdates={
                'state': {
                    'Value': CLOSED,
                    'Action': 'PUT',
                }
            }
        )
