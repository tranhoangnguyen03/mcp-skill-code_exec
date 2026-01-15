from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from typing import Iterable


@dataclass(frozen=True)
class Employee:
    id: int
    name: str
    dept: str
    role: str
    status: str
    hire_date: date
    manager: str
    slack_id: str
    manager_slack_id: str


_TODAY = date.today()
_EMPLOYEES = [
    Employee(
        id=101,
        name="Alice Chen",
        dept="Engineering",
        role="Software Engineer",
        status="Active",
        hire_date=_TODAY,
        manager="Dana Patel",
        slack_id="U_ALICE",
        manager_slack_id="U_DANA",
    ),
    Employee(
        id=102,
        name="Bob Smith",
        dept="Sales",
        role="Account Executive",
        status="Active",
        hire_date=_TODAY,
        manager="Evan Lee",
        slack_id="U_BOB",
        manager_slack_id="U_EVAN",
    ),
    Employee(
        id=103,
        name="Charlie Davis",
        dept="Engineering",
        role="DevOps Engineer",
        status="Active",
        hire_date=_TODAY,
        manager="Dana Patel",
        slack_id="U_CHARLIE",
        manager_slack_id="U_DANA",
    ),
    Employee(
        id=104,
        name="Priya Nair",
        dept="Engineering",
        role="QA Engineer",
        status="Active",
        hire_date=_TODAY - timedelta(days=90),
        manager="Dana Patel",
        slack_id="U_PRIYA",
        manager_slack_id="U_DANA",
    ),
    Employee(
        id=105,
        name="Maya Lopez",
        dept="People",
        role="HR Generalist",
        status=f"Offboarding ({(_TODAY + timedelta(days=14)).isoformat()})",
        hire_date=_TODAY - timedelta(days=730),
        manager="Nina Kim",
        slack_id="U_MAYA",
        manager_slack_id="U_NINA",
    ),
    Employee(
        id=106,
        name="Jordan Lee",
        dept="Engineering",
        role="Engineering Manager",
        status="Active",
        hire_date=_TODAY - timedelta(days=1100),
        manager="Riley Kim",
        slack_id="U_JORDAN",
        manager_slack_id="U_RILEY",
    ),
    Employee(
        id=107,
        name="Riley Kim",
        dept="People",
        role="People Ops Manager",
        status="Active",
        hire_date=_TODAY - timedelta(days=1600),
        manager="Evan Park",
        slack_id="U_RILEY",
        manager_slack_id="U_EVANP",
    ),
    Employee(
        id=108,
        name="Morgan Patel",
        dept="Sales",
        role="Account Executive",
        status="Active",
        hire_date=_TODAY - timedelta(days=900),
        manager="Evan Lee",
        slack_id="U_MORGAN",
        manager_slack_id="U_EVAN",
    ),
]


def list_employees(status: str | None = None) -> list[dict]:
    if isinstance(status, dict):
        status = status.get("status")
    employees: Iterable[Employee] = _EMPLOYEES
    if status:
        employees = [e for e in employees if e.status == status]
    return [_to_dict(e) for e in employees]


def get_employee(employee_id: int) -> dict | None:
    if isinstance(employee_id, dict):
        employee_id = employee_id.get("employee_id")
    for e in _EMPLOYEES:
        if e.id == employee_id:
            return _to_dict(e)
    return None


def search_employees(query: str) -> list[dict]:
    if isinstance(query, dict):
        query = query.get("query") or ""
    q = query.strip().lower()
    if not q:
        return []
    matches = [
        e
        for e in _EMPLOYEES
        if q in e.name.lower() or q in e.dept.lower() or q in e.role.lower()
    ]
    return [_to_dict(e) for e in matches]


def get_new_hires(start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    if isinstance(start_date, dict):
        payload = start_date
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
    start = _parse_date(start_date) if start_date else date.today()
    end = _parse_date(end_date) if end_date else date.today()
    if start > end:
        start, end = end, start
    hires = [e for e in _EMPLOYEES if start <= e.hire_date <= end]
    return [_to_dict(e) for e in hires]


def get_todays_hires() -> list[dict]:
    today = date.today()
    hires = [e for e in _EMPLOYEES if e.hire_date == today]
    return [_to_dict(e) for e in hires]


def get_anniversary_employees(days_ahead: int = 0) -> list[dict]:
    if isinstance(days_ahead, dict):
        days_ahead = int(days_ahead.get("days_ahead") or 0)
    target = date.today() + timedelta(days=days_ahead)
    matches = [
        e
        for e in _EMPLOYEES
        if (e.hire_date.month, e.hire_date.day) == (target.month, target.day)
    ]
    return [_to_dict(e) for e in matches]


def get_probation_checkins(days_since_hire: int = 90, window_days: int = 7) -> list[dict]:
    if isinstance(days_since_hire, dict):
        payload = days_since_hire
        days_since_hire = int(payload.get("days_since_hire") or 90)
        window_days = int(payload.get("window_days") or 7)
    today = date.today()
    start = today - timedelta(days=days_since_hire + window_days)
    end = today - timedelta(days=days_since_hire - window_days)
    matches = [e for e in _EMPLOYEES if start <= e.hire_date <= end]
    return [_to_dict(e) for e in matches]


def update_employee(employee_id: int, updates: dict | None = None) -> dict:
    if isinstance(employee_id, dict):
        payload = employee_id
        employee_id = payload.get("employee_id")
        updates = payload.get("updates") or {}
    updates = updates or {}
    for idx, e in enumerate(_EMPLOYEES):
        if e.id != employee_id:
            continue

        allowed = {
            "dept",
            "role",
            "status",
            "manager",
            "slack_id",
            "manager_slack_id",
        }
        filtered = {k: v for k, v in updates.items() if k in allowed}
        updated = replace(e, **filtered)
        _EMPLOYEES[idx] = updated
        return _to_dict(updated)

    raise ValueError(f"Unknown employee_id={employee_id}")


def mark_offboarding(employee_id: int, effective_date: str | None = None) -> dict:
    if isinstance(employee_id, dict):
        payload = employee_id
        employee_id = payload.get("employee_id")
        effective_date = payload.get("effective_date")
    employee = get_employee(employee_id)
    if not employee:
        raise ValueError(f"Unknown employee_id={employee_id}")
    effective = _parse_date(effective_date) if effective_date else date.today()
    updated = update_employee(employee_id, {"status": f"Offboarding ({effective.isoformat()})"})
    return updated


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _to_dict(e: Employee) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "dept": e.dept,
        "role": e.role,
        "status": e.status,
        "hire_date": e.hire_date.isoformat(),
        "manager": e.manager,
        "slack_id": e.slack_id,
        "manager_slack_id": e.manager_slack_id,
    }
