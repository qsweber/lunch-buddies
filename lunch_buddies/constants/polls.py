from lunch_buddies.models.polls import Choice, ChoiceList


CHOICES = ChoiceList([
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
])

CREATED = 'CREATED'
CLOSED = 'CLOSED'

POLL_STATES = [
    CREATED,
    CLOSED,
]
