import datetime
import random
from uuid import UUID

import pytest

from lunch_buddies.models.poll_responses import PollResponse
import lunch_buddies.actions.close_poll as module


@pytest.mark.parametrize(
    'elements, group_size, smallest_group, expected',
    [
        (list(range(11)), 5, 3, [[2, 7, 4, 1, 8, 6], [3, 9, 0, 5, 10]]),
        (list(range(14)), 5, 3, [[1, 11, 5, 3, 7], [10, 2, 8, 4, 9], [13, 6, 12, 0]]),
        ([1], 10, 8, [[1]]),
        ([1, 2], 2, 2, [[1, 2]]),
    ]
)
def test_get_groups(elements, group_size, smallest_group, expected):
    random.seed(0)

    actual = module.get_groups(elements, group_size, smallest_group)

    assert actual == expected


def test_group_by_answer():
    poll_responses = [
        PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U3LTPT61J', created_at=datetime.datetime(2018, 1, 31, 16, 43, 19, 93329), response='yes_1230'),
        PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U69J2B8E8', created_at=datetime.datetime(2018, 1, 31, 16, 43, 5, 494358), response='yes_1145'),
        PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U71ECE86R', created_at=datetime.datetime(2018, 1, 31, 16, 43, 26, 9092), response='no'),
        PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U799LRKSA', created_at=datetime.datetime(2018, 1, 31, 16, 43, 36, 221596), response='yes_1145'),
    ]

    expected = {
        'yes_1145': [
            PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U69J2B8E8', created_at=datetime.datetime(2018, 1, 31, 16, 43, 5, 494358), response='yes_1145'),
            PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U799LRKSA', created_at=datetime.datetime(2018, 1, 31, 16, 43, 36, 221596), response='yes_1145'),
        ],
        'yes_1230': [
            PollResponse(callback_id=UUID('450c4b9d-267b-431e-97b9-e3cb32d233c4'), user_id='U3LTPT61J', created_at=datetime.datetime(2018, 1, 31, 16, 43, 19, 93329), response='yes_1230'),
        ],
    }

    actual = module._group_by_answer(poll_responses)

    assert actual == expected
