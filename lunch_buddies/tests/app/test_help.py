import os

import pytest

import lunch_buddies.app as module
from lunch_buddies.constants.help import APP_EXPLANATION


def test_help_fails_without_verification_token():
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
    }

    os.environ['VERIFICATION_TOKEN'] = 'wrong_verification_token'

    with pytest.raises(Exception) as excinfo:
        module._help(request_form)

    assert 'you are not authorized to call this URL' == str(excinfo.value)


def test_help():
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    outgoing_message = module._help(request_form)

    assert outgoing_message == {'text': APP_EXPLANATION}
