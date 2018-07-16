from lunch_buddies.dao.base import Dao
from lunch_buddies.models.teams import Team


class TeamsDao(Dao[Team]):
    def __init__(self):
        super(TeamsDao, self).__init__(Team, 'Team')
