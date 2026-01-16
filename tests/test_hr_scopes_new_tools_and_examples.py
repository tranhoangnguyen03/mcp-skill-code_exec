from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

from agent_workspace.hr_agent_v2.agent import _extract_logic_flow_steps
from agent_workspace.hr_agent_v2.skill_registry import SkillRegistry


@contextmanager
def _sys_path(path: Path):
    p = str(path)
    sys.path.insert(0, p)
    try:
        yield
    finally:
        try:
            sys.path.remove(p)
        except ValueError:
            pass


def test_new_mcp_tools_google_calendar_create_and_list_events():
    repo_root = Path(__file__).resolve().parents[1]
    v2_tools_root = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools"

    with _sys_path(v2_tools_root):
        from mcp_tools import google_calendar

        event = google_calendar.create_event(
            {
                "email": "alice@company.com",
                "title": "OOO: Vacation",
                "start_time": "2023-12-25T09:00:00",
                "end_time": "2023-12-29T17:00:00",
            }
        )
        assert event["id"].startswith("evt_")
        assert event["email"] == "alice@company.com"

        events = google_calendar.get_events({"email": "alice@company.com"})
        assert any(e["id"] == event["id"] for e in events)


def test_new_mcp_tools_gmail_set_and_get_auto_responder():
    repo_root = Path(__file__).resolve().parents[1]
    v2_tools_root = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools"

    with _sys_path(v2_tools_root):
        from mcp_tools import gmail

        saved = gmail.set_auto_responder(
            email="alice@company.com",
            start_date="2023-12-25",
            end_date="2023-12-29",
            message="I am out of office.",
        )
        assert saved["email"] == "alice@company.com"
        assert saved["enabled"] is True

        fetched = gmail.get_auto_responder({"email": "alice@company.com"})
        assert fetched is not None
        assert fetched["message"] == "I am out of office."


def test_new_mcp_tools_lattice_create_cycle_and_eligibility():
    repo_root = Path(__file__).resolve().parents[1]
    v2_tools_root = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools"

    with _sys_path(v2_tools_root):
        from mcp_tools import lattice

        cycle = lattice.create_cycle(name="Q4 Review", due_date="2024-01-31")
        assert cycle["id"].startswith("cycle_")
        assert cycle["status"] == "active"

        eligible = lattice.get_eligible_employees(min_tenure_days=90)
        assert len(eligible) == 2
        names = {u["name"] for u in eligible}
        assert "Bob Smith" in names
        assert "Charlie Davis" in names


def test_hr_scopes_new_examples_are_discoverable_and_have_logic_flow_steps():
    repo_root = Path(__file__).resolve().parents[1]
    skills_dir = repo_root / "agent_workspace" / "skills_v2"
    registry = SkillRegistry(skills_dir)

    skills = registry.list_skills()
    by_name = {s.name: s for s in skills}

    assert "Leave & Absence Management" in by_name
    assert "Performance Review Cycle" in by_name

    for name in ["Leave & Absence Management", "Performance Review Cycle"]:
        steps = _extract_logic_flow_steps(by_name[name].content)
        assert steps, f"expected non-empty logic flow steps for {name}"
