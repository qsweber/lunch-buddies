import json
import os

import lunch_buddies.actions.auth as module
from lunch_buddies.types import Auth
from lunch_buddies.lib.service_context import service_context
from lunch_buddies.actions.tests.fixtures import oath_response, team, dynamo_team, stripe_customer


def test_auth(mocker, mocked_slack):
    mocker.patch.object(
        service_context.daos.teams,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
    mocker.patch.object(
        service_context.daos.teams,
        '_read_internal',
        auto_spec=True,
        return_value=[],
    )
    mocker.patch.object(
        service_context.daos.team_settings,
        '_create_internal',
        auto_spec=True,
        return_value=True,
    )
    mocker.patch.object(
        service_context.clients.http,
        'get',
        auto_spec=True,
        return_value=mocker.Mock(text=json.dumps(oath_response)),
    )
    mocker.patch.object(
        module,
        '_get_created_at',
        auto_spec=True,
        return_value=team.created_at,
    )
    mocker.patch.object(
        service_context.clients.slack,
        'get_user_name_email',
        auto_spec=True,
        return_value=('Test Name', 'test@example.com'),
    )
    mocker.patch.object(
        service_context.clients.stripe,
        'create_customer',
        auto_spec=True,
        return_value=stripe_customer,
    )

    os.environ['CLIENT_ID'] = 'test_client_id'
    os.environ['CLIENT_SECRET'] = 'test_client_secret'

    module.auth(
        Auth(code='test_code'),
        service_context,
    )

    service_context.daos.teams._create_internal.assert_called_with(dynamo_team)
    service_context.daos.team_settings._create_internal.assert_called_with(
        {
            'team_id': team.team_id,
            'feature_notify_in_channel': 1,
        },
    )
    service_context.clients.slack.post_message.assert_called_with(
        bot_access_token=team.bot_access_token,
        channel='fake-user-id',
        as_user=True,
        text='Thanks for installing Lunch Buddies! To get started, invite me to any channel and say "@Lunch Buddies create"',
    )
    service_context.clients.http.get.assert_called_with(
        url='https://slack.com/api/oauth.access',
        params={'client_id': 'test_client_id', 'client_secret': 'test_client_secret', 'code': 'test_code'},
    )
    service_context.clients.slack.get_user_name_email.assert_called_with(
        bot_access_token=team.bot_access_token,
        user_id='fake-user-id',
    )
    service_context.clients.stripe.create_customer.assert_called_with(
        name='Test Name',
        email='test@example.com',
        team_name='fake-team-name',
    )
