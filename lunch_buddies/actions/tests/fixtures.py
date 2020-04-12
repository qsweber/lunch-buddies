from datetime import datetime

from lunch_buddies.models.teams import Team
from lunch_buddies.clients.stripe import Customer


dynamo_team = {
    'team_id': '123',
    'access_token': 'fake-token',
    'name': 'fake-team-name',
    'stripe_customer_id': 'fake-stripe-customer-id',
    'bot_access_token': 'fake-bot-token',
    'created_at': 1585153363.983078,
}

team = Team(
    team_id='123',
    access_token='fake-token',
    name='fake-team-name',
    stripe_customer_id='fake-stripe-customer-id',
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
