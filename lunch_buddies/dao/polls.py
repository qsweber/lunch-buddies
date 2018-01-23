from lunch_buddies.dao.base import Dao
from lunch_buddies.models.polls import Poll


class PollsDao(Dao):
    def __init__(self):
        super(PollsDao, self).__init__(Poll)

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
        return self.read('team_id', team_id)[-1]
