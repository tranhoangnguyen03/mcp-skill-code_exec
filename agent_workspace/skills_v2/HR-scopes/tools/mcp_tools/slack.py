from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SlackMessage:
    channel: str
    user_id: str | None
    text: str


_MESSAGES: list[SlackMessage] = []


def send_dm(user_id: str, message: str | None = None) -> None:
    if isinstance(user_id, dict):
        payload = user_id
        user_id = payload.get("user_id")
        message = payload.get("message")
    _MESSAGES.append(SlackMessage(channel="dm", user_id=user_id, text=message))
    print(f'   [Slack] Sent DM to {user_id}: "{message}"')


def post_message(channel: str, message: str | None = None) -> None:
    if isinstance(channel, dict):
        payload = channel
        channel = payload.get("channel")
        message = payload.get("message")
    _MESSAGES.append(SlackMessage(channel=channel, user_id=None, text=message))
    print(f'   [Slack] Posted in {channel}: "{message}"')


def list_messages(channel: str | None = None) -> list[dict]:
    if isinstance(channel, dict):
        channel = channel.get("channel")
    msgs = _MESSAGES
    if channel:
        msgs = [m for m in msgs if m.channel == channel]
    return [{"channel": m.channel, "user_id": m.user_id, "text": m.text} for m in msgs]
