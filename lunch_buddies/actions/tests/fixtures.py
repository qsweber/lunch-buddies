import uuid
from datetime import datetime

from lunch_buddies.models.polls import Poll, Choice
from lunch_buddies.models.teams import Team
from lunch_buddies.clients.stripe import Customer


dynamo_team = {
    'team_id': '123',
    'access_token': 'fake-token',
    'name': 'fake-team-name',
    'bot_access_token': 'fake-bot-token',
    'created_at': 1585153363.983078,
}

team = Team(
    team_id='123',
    access_token='fake-token',
    name='fake-team-name',
    bot_access_token='fake-bot-token',
    created_at=datetime.fromtimestamp(1585153363.983078),
)

oath_response = {
    'ok': True,
    'access_token': 'fake-token',
    'scope': 'identify,bot,commands,channels:write,chat:write:bot',
    'user_id': 'fake-user-id',
    'team_name': 'fake-team-name',
    'team_id': '123',
    'bot': {
        'bot_user_id': 'U8PRM6XHN',
        'bot_access_token': 'fake-bot-token'
    }
}

stripe_customer = Customer(
    id='fake-stripe-customer-id'
)

poll = Poll(
    team_id='123',
    created_at=datetime.fromtimestamp(1522117983.551714),
    channel_id='test_channel_id',
    created_by_user_id='456',
    callback_id=uuid.UUID('f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa'),
    state='CREATED',
    choices=[
        Choice(
            key='yes_1130',
            is_yes=True,
            time='11:30',
            display_text='Yes (11:30)',
        ),
        Choice(
            key='yes_1230',
            is_yes=True,
            time='12:30',
            display_text='Yes (12:30)',
        ),
        Choice(
            key='no',
            is_yes=False,
            time='',
            display_text='No',
        ),
    ],
    group_size=6,
)

dynamo_poll = {
    'team_id': '123',
    'created_at': 1522117983.551714,
    'channel_id': 'test_channel_id',
    'created_by_user_id': '456',
    'callback_id': 'f0d101f9-9aaa-4899-85c8-aa0a2dbb0aaa',
    'state': 'CREATED',
    'choices': '[{"key": "yes_1130", "is_yes": true, "time": "11:30", "display_text": "Yes (11:30)"}, {"key": "yes_1230", "is_yes": true, "time": "12:30", "display_text": "Yes (12:30)"}, {"key": "no", "is_yes": false, "time": "", "display_text": "No"}]',
    'group_size': 6,
}
