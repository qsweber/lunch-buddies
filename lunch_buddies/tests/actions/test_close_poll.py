import random

import pytest

import lunch_buddies.actions.close_poll as module


@pytest.mark.parametrize(
    'elements, group_size, smallest_group, expected',
    [
        (list(range(11)), 5, 3, [[2, 7, 4, 1, 8, 6], [3, 9, 0, 5, 10]]),
        (list(range(14)), 5, 3, [[1, 11, 5, 3, 7], [10, 2, 8, 4, 9], [13, 6, 12, 0]]),
    ]
)
def test_get_groups(elements, group_size, smallest_group, expected):
    random.seed(0)

    actual = module.get_groups(elements, group_size, smallest_group)

    assert actual == expected
