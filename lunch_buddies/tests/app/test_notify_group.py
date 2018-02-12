from datetime import datetime
import random

from lunch_buddies.actions import notify_group as notify_group_module
from lunch_buddies.constants import queues as queues_constants
from lunch_buddies.clients.sqs import SqsClient
from lunch_buddies.clients.slack import SlackClient
from lunch_buddies.dao.teams import TeamsDao
from lunch_buddies.models.teams import Team
import lunch_buddies.app as module


def test_notify_group_from_queue(mocker):
    sqs_client = SqsClient(queues_constants.QUEUES)
    mocked_receive_message_internal = mocker.patch.object(
        sqs_client,
        '_receive_message_internal',
        auto_spec=True,
    )
    mocked_receive_message_internal.side_effect = [
        {
            'Messages': [{
                'Body': '{"team_id": "123", "response": "yes_1145", "user_ids": ["user_id_one", "user_id_two"]}',
                'ReceiptHandle': 'test receipt handle',
            }]
        },
        None,
        None,
        None,
        None,
    ]
    mocker.patch.object(
        sqs_client,
        '_delete_message_internal',
        auto_spec=True,
    )

    slack_client = SlackClient()

    teams_dao = TeamsDao()
    created_at = datetime.now()
    mocker.patch.object(
        teams_dao,
        '_read_internal',
        auto_spec=True,
        return_value=[{
            'team_id': '123',
            'access_token': 'fake-token',
            'bot_access_token': 'fake-bot-token',
            'created_at': created_at.timestamp(),
        }]
    )

    mocker.patch.object(
        slack_client,
        'open_conversation',
        auto_spec=True,
        return_value={'channel': {'id': 'new_group_message_channel'}}
    )

    mocked_post_message = mocker.patch.object(
        slack_client,
        'post_message',
        auto_spec=True,
        return_value=True,
    )

    random.seed(0)

    module._read_from_queue(
        queues_constants.GROUPS_TO_NOTIFY,
        notify_group_module.notify_group,
        sqs_client,
        slack_client,
        None,
        None,
        teams_dao,
    )

    assert mocked_post_message.call_count == 1

    mocked_post_message.assert_called_with(
        team=Team(
            team_id='123',
            access_token='fake-token',
            bot_access_token='fake-bot-token',
            created_at=created_at,
        ),
        channel='new_group_message_channel',
        text='Hello! This is your lunch group for today. You all should meet somewhere at `11:45`. I am selecting <@user_id_two> to be in charge of picking the location.',
    )
