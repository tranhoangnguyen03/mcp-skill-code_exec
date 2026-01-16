from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class AutoResponder:
    email: str
    start_date: str
    end_date: str
    message: str
    enabled: bool = True

_SETTINGS = {}

def set_auto_responder(email: str, start_date: str, end_date: str, message: str) -> dict:
    """Sets an out-of-office auto-responder."""
    if isinstance(email, dict):
        payload = email
        email = payload.get("email")
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        message = payload.get("message")

    responder = AutoResponder(
        email=email,
        start_date=start_date,
        end_date=end_date,
        message=message
    )
    _SETTINGS[email] = responder
    return _to_dict(responder)

def get_auto_responder(email: str) -> dict | None:
    """Gets the current auto-responder settings for a user."""
    if isinstance(email, dict):
        email = email.get("email")
        
    responder = _SETTINGS.get(email)
    if not responder:
        return None
    return _to_dict(responder)

def _to_dict(r: AutoResponder) -> dict:
    return {
        "email": r.email,
        "start_date": r.start_date,
        "end_date": r.end_date,
        "message": r.message,
        "enabled": r.enabled
    }
