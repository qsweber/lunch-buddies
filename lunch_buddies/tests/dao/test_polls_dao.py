from datetime import datetime
import uuid

from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.models.polls import Poll
from lunch_buddies.actions.create_poll import get_choices_from_message_text


def test_roundtrip_encoding():
    polls_dao = PollsDao()

    poll = Poll(
        team_id='123',
        created_at=datetime.now(),
        created_by_user_id='456',
        callback_id=uuid.uuid4(),
        state='CREATED',
        choices=get_choices_from_message_text('1230'),
    )

    after = polls_dao._as_model(polls_dao._as_dynamo_object(poll))

    assert after == poll
