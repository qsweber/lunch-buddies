from lunch_buddies.dao.base import Dao
from lunch_buddies.models.groups import Group


class GroupsDao(Dao):
    def __init__(self):
        super(GroupsDao, self).__init__(Group)
