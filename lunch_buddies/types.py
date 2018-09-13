from typing import NamedTuple

from uuid import UUID

# From HTTP


class Auth(NamedTuple):
    code: str


class BotMention(NamedTuple):
    team_id: str
    channel_id: str
    user_id: str
    text: str


class ClosePoll(NamedTuple):
    team_id: str
    channel_id: str
    user_id: str
    text: str


class CreatePoll(NamedTuple):
    text: str
    team_id: str
    channel_id: str
    user_id: str


class ListenToPoll(NamedTuple):
    original_message: dict
    team_id: str
    user_id: str
    choice_key: str
    action_ts: float
    callback_id: UUID


# From SQS


class PollsToStartMessage(NamedTuple):
    team_id: str
    channel_id: str
    user_id: str
    text: str


class UsersToPollMessage(NamedTuple):
    team_id: str
    user_id: str
    callback_id: UUID


class PollsToCloseMessage(NamedTuple):
    team_id: str
    channel_id: str
    user_id: str


class GroupsToNotifyMessage(NamedTuple):
    team_id: str
    callback_id: UUID
    response: str
    user_ids: list
