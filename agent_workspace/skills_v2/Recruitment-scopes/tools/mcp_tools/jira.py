from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Ticket:
    id: str
    project: str
    summary: str
    priority: str
    status: str = "Open"


_SEQ = 100
_TICKETS: dict[str, Ticket] = {}


def create_ticket(project: str, summary: str | None = None, priority: str | None = None) -> str:
    if isinstance(project, dict):
        payload = project
        project = payload.get("project")
        summary = payload.get("summary")
        priority = payload.get("priority")
    global _SEQ
    _SEQ += 1
    ticket_id = f"{project}-{_SEQ}"
    _TICKETS[ticket_id] = Ticket(
        id=ticket_id,
        project=project,
        summary=summary,
        priority=priority,
    )
    print(f"   [Jira] Created ticket {ticket_id}: '{summary}' (Priority: {priority})")
    return ticket_id


def add_comment(ticket_id: str, comment: str) -> None:
    if isinstance(ticket_id, dict):
        payload = ticket_id
        ticket_id = payload.get("ticket_id")
        comment = payload.get("comment")
    _require_ticket(ticket_id)
    print(f"   [Jira] Comment on {ticket_id}: '{comment}'")


def transition_ticket(ticket_id: str, status: str) -> None:
    if isinstance(ticket_id, dict):
        payload = ticket_id
        ticket_id = payload.get("ticket_id")
        status = payload.get("status")
    t = _require_ticket(ticket_id)
    t.status = status
    print(f"   [Jira] Transitioned {ticket_id} -> {status}")


def get_ticket(ticket_id: str) -> dict | None:
    if isinstance(ticket_id, dict):
        ticket_id = ticket_id.get("ticket_id")
    t = _TICKETS.get(ticket_id)
    if not t:
        return None
    return {"id": t.id, "project": t.project, "summary": t.summary, "priority": t.priority, "status": t.status}


def search_tickets(project: str | None = None, status: str | None = None) -> list[dict]:
    if isinstance(project, dict):
        payload = project
        project = payload.get("project")
        status = payload.get("status")
    tickets = list(_TICKETS.values())
    if project:
        tickets = [t for t in tickets if t.project == project]
    if status:
        tickets = [t for t in tickets if t.status == status]
    return [{"id": t.id, "project": t.project, "summary": t.summary, "priority": t.priority, "status": t.status} for t in tickets]


def _require_ticket(ticket_id: str) -> Ticket:
    t = _TICKETS.get(ticket_id)
    if not t:
        raise ValueError(f"Unknown ticket_id={ticket_id}")
    return t

