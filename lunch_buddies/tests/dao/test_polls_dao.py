from datetime import datetime
import uuid

from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.models.polls import Poll
from lunch_buddies.actions.create_poll import parse_message_text


def test_roundtrip_encoding():
    polls_dao = PollsDao()

    choices, group_size = parse_message_text('1230')

    poll = Poll(
        team_id='123',
        created_at=datetime.now(),
        channel_id='test_channel_id',
        created_by_user_id='456',
        callback_id=uuid.uuid4(),
        state='CREATED',
        choices=choices,
        group_size=group_size,
    )

    after = polls_dao._as_model(polls_dao._as_dynamo_object(poll))

    assert after == poll
