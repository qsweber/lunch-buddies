from datetime import datetime
import uuid

from lunch_buddies.dao.polls import PollsDao
from lunch_buddies.models.polls import Poll
from lunch_buddies.actions.create_poll import get_choices_from_message_text


def test_handles_null_values_in_dynamo(mocker):
    polls_dao = PollsDao()

    created_at = 1522117983.551714

    mocker.patch.object(
        polls_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[
            {
                'team_id': '123',
                'created_at': 1522117983.551714,
                # 'channel_id': 'test_channel_id',
                'created_by_user_id': '456',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': 'CREATED',
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
            },
        ]
    )

    polls = polls_dao.read()

    expected_polls = [
        Poll(
            team_id='123',
            created_at=datetime.fromtimestamp(created_at),
            channel_id=None,
            created_by_user_id='456',
            callback_id=uuid.UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa'),
            state='CREATED',
            choices=get_choices_from_message_text('1200'),
        ),
    ]

    assert polls == expected_polls
