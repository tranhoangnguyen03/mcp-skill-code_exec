from pathlib import Path

from agent_workspace.hr_agent_v2.skill_registry import SkillRegistry


def test_skill_registry_v2_finds_hr_scopes_skill():
    repo_root = Path(__file__).resolve().parents[1]
    registry = SkillRegistry(repo_root / "agent_workspace" / "skills_v2")
    skills = registry.list_skills()
    names = {s.name for s in skills}
    assert "Onboard New Hires" in names
    assert "Offboard Employee" in names
    assert "Probation Check-in Reminders" in names
