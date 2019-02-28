from lunch_buddies.dao.base import Dao
from lunch_buddies.models.team_settings import TeamSettings


class TeamSettingsDao(Dao):
    def __init__(self):
        super(TeamSettingsDao, self).__init__(TeamSettings)
