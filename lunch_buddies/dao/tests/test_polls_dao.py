from datetime import datetime
import uuid
import pytest

from lunch_buddies.lib.service_context import service_context
from lunch_buddies.models.polls import Poll, Choice


@pytest.mark.parametrize(
    'model, dynamo',
    [
        (
            Poll(
                team_id='123',
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id='test_channel_id',
                created_by_user_id='456',
                callback_id=uuid.UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa'),
                state='CREATED',
                choices=[
                    Choice(
                        key='yes_1200',
                        is_yes=True,
                        time='12:00',
                        display_text='Yes (12:00)',
                    ),
                    Choice(
                        key='no',
                        is_yes=False,
                        time='',
                        display_text='No',
                    ),
                ],
                group_size=6,
            ),
            {
                'team_id': '123',
                'created_at': 1522117983.551714,
                'channel_id': 'test_channel_id',
                'created_by_user_id': '456',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': 'CREATED',
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': 6,
            }
        ),
        (
            Poll(
                team_id='123',
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id=None,
                created_by_user_id='456',
                callback_id=uuid.UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa'),
                state='CREATED',
                choices=[
                    Choice(
                        key='yes_1200',
                        is_yes=True,
                        time='12:00',
                        display_text='Yes (12:00)',
                    ),
                    Choice(
                        key='no',
                        is_yes=False,
                        time='',
                        display_text='No',
                    ),
                ],
                group_size=6,
            ),
            {
                'team_id': '123',
                'created_at': 1522117983.551714,
                'channel_id': None,
                'created_by_user_id': '456',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': 'CREATED',
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': 6,
            }
        )
    ]
)
def test_roundtrip(model, dynamo):
    to_dynamo = service_context.daos.polls.convert_to_dynamo(model)

    assert to_dynamo == dynamo

    from_dynamo = service_context.daos.polls.convert_from_dynamo(to_dynamo)

    assert from_dynamo.channel_id == model.channel_id


@pytest.mark.parametrize(
    'dynamo, expected',
    [
        (
            {
                'team_id': '123',
                'created_at': 1522117983.551714,
                'channel_id': 'test_channel_id',
                'created_by_user_id': '456',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': 'CREATED',
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': 6,
            },
            Poll(
                team_id='123',
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id='test_channel_id',
                created_by_user_id='456',
                callback_id=uuid.UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa'),
                state='CREATED',
                choices=[
                    Choice(
                        key='yes_1200',
                        is_yes=True,
                        time='12:00',
                        display_text='Yes (12:00)',
                    ),
                    Choice(
                        key='no',
                        is_yes=False,
                        time='',
                        display_text='No',
                    ),
                ],
                group_size=6,
            ),
        ),
        (
            {
                'team_id': '123',
                'created_at': 1522117983.551714,
                'created_by_user_id': '456',
                'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
                'state': 'CREATED',
                'choices': '[{"key": "yes_1200", "is_yes": true, "time": "12:00", "display_text": "Yes (12:00)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
                'group_size': 6,
            },
            Poll(
                team_id='123',
                created_at=datetime.fromtimestamp(1522117983.551714),
                channel_id=None,
                created_by_user_id='456',
                callback_id=uuid.UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa'),
                state='CREATED',
                choices=[
                    Choice(
                        key='yes_1200',
                        is_yes=True,
                        time='12:00',
                        display_text='Yes (12:00)',
                    ),
                    Choice(
                        key='no',
                        is_yes=False,
                        time='',
                        display_text='No',
                    ),
                ],
                group_size=6,
            ),
        )
    ]
)
def test_from_dynamo(mocker, dynamo, expected):
    mocker.patch.object(
        service_context.daos.polls,
        '_read_internal',
        auto_spec=True,
        return_value=[dynamo]
    )

    poll = service_context.daos.polls.find_by_callback_id_or_die('123', expected.callback_id)

    assert poll == expected
