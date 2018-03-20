import os

import pytest

import lunch_buddies.app.http as module


def test_validate_request_token():
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': 'help',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    result = module._validate_request_token(request_form)

    assert result is True


def test_validate_request_token_finds_dev_token():
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_dev_verification_token',
        'text': 'help',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'
    os.environ['VERIFICATION_TOKEN'] = 'fake_dev_verification_token'

    result = module._validate_request_token(request_form)

    assert result is True


def test_validate_request_token_errors_if_does_not_match_either():
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'foo',
        'text': 'help',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'
    os.environ['VERIFICATION_TOKEN'] = 'fake_dev_verification_token'

    with pytest.raises(Exception) as excinfo:
        module._validate_request_token(request_form)

    assert 'you are not authorized to call this URL' == str(excinfo.value)
