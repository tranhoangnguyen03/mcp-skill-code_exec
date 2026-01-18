from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    email: str
    title: str
    start_time: str
    end_time: str
    status: str = "confirmed"


_EVENTS = []


def create_event(
    email: str,
    title: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    if isinstance(email, dict):
        payload = email
        email = payload.get("email")
        title = payload.get("title")
        start_time = payload.get("start_time")
        end_time = payload.get("end_time")

    if not email or not title or not start_time or not end_time:
        raise ValueError("email, title, start_time, and end_time are required")

    event_id = f"evt_{len(_EVENTS) + 100}"
    event = CalendarEvent(
        id=event_id,
        email=email,
        title=title,
        start_time=start_time,
        end_time=end_time,
    )
    _EVENTS.append(event)
    return _to_dict(event)


def get_events(email: str, date_str: str | None = None) -> list[dict]:
    if isinstance(email, dict):
        payload = email
        email = payload.get("email")
        date_str = payload.get("date")

    matches = [e for e in _EVENTS if e.email == email]
    if date_str:
        matches = [e for e in matches if e.start_time.startswith(date_str)]
    return [_to_dict(e) for e in matches]


def _to_dict(e: CalendarEvent) -> dict:
    return {
        "id": e.id,
        "email": e.email,
        "title": e.title,
        "start_time": e.start_time,
        "end_time": e.end_time,
        "status": e.status,
    }

