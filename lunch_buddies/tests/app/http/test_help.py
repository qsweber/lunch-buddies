import datetime
import os

import pytest

import lunch_buddies.app.http as module
from lunch_buddies.constants.help import APP_EXPLANATION
from lunch_buddies.dao.teams import TeamsDao


def test_help_fails_without_verification_token(mocker):
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': '',
    }

    os.environ['VERIFICATION_TOKEN'] = 'wrong_verification_token'

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': datetime.datetime.now().timestamp(),
        }]
    )

    with pytest.raises(Exception) as excinfo:
        module._help(request_form, teams_dao, '')

    assert 'you are not authorized to call this URL' == str(excinfo.value)


def test_help_fails_without_authorized_team(mocker):
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
        'text': '',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[]
    )

    with pytest.raises(Exception) as excinfo:
        module._help(request_form, teams_dao, '')

    assert 'your team is not authorized for this app' == str(excinfo.value)


def test_help(mocker):
    request_form = {
        'team_id': '123',
        'user_id': 'abc',
        'token': 'fake_verification_token',
    }

    os.environ['VERIFICATION_TOKEN'] = 'fake_verification_token'

    teams_dao = TeamsDao()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': datetime.datetime.now().timestamp(),
        }]
    )

    outgoing_message = module._help(request_form, teams_dao)

    assert outgoing_message == {'text': APP_EXPLANATION}
