from lunch_buddies.dao.base import Dao
from lunch_buddies.models.poll_responses import PollResponse


class PollResponsesDao(Dao):
    def __init__(self):
        super(PollResponsesDao, self).__init__(PollResponse)
