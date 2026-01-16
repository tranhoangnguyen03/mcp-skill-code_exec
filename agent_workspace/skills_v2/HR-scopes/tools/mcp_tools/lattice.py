from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

@dataclass(frozen=True)
class ReviewCycle:
    id: str
    name: str
    due_date: str
    status: str = "active"

@dataclass(frozen=True)
class LatticeUser:
    id: str
    name: str
    start_date: str  # YYYY-MM-DD
    manager_id: str

_CYCLES = []

# Mock database of users with varying tenure
_TODAY = date.today()
_USERS = [
    LatticeUser("101", "Alice Chen", (_TODAY - timedelta(days=30)).isoformat(), "102"), # New hire (< 3 months)
    LatticeUser("102", "Bob Smith", (_TODAY - timedelta(days=400)).isoformat(), "103"), # > 1 year
    LatticeUser("103", "Charlie Davis", (_TODAY - timedelta(days=120)).isoformat(), "104"), # > 3 months
]

def create_cycle(name: str, due_date: str) -> dict:
    """Creates a new performance review cycle."""
    if isinstance(name, dict):
        payload = name
        name = payload.get("name")
        due_date = payload.get("due_date")

    cycle_id = f"cycle_{len(_CYCLES) + 1}"
    cycle = ReviewCycle(id=cycle_id, name=name, due_date=due_date)
    _CYCLES.append(cycle)
    return _to_dict(cycle)

def get_eligible_employees(min_tenure_days: int = 90) -> list[dict]:
    """Returns employees who have been employed for at least min_tenure_days."""
    if isinstance(min_tenure_days, dict):
        min_tenure_days = int(min_tenure_days.get("min_tenure_days", 90))

    cutoff_date = _TODAY - timedelta(days=min_tenure_days)
    
    eligible = []
    for u in _USERS:
        start = date.fromisoformat(u.start_date)
        if start <= cutoff_date:
            eligible.append({
                "id": u.id,
                "name": u.name,
                "start_date": u.start_date,
                "manager_id": u.manager_id
            })
    return eligible

def _to_dict(c: ReviewCycle) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "due_date": c.due_date,
        "status": c.status
    }
