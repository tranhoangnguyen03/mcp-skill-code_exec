from pathlib import Path

from agent_workspace.hr_agent.skill_registry import SkillRegistry


def test_skill_registry_finds_skills():
    repo_root = Path(__file__).resolve().parents[1]
    registry = SkillRegistry(repo_root / "agent_workspace" / "skills")
    skills = registry.list_skills()
    names = {s.name for s in skills}
    assert "onboarding_new_hires" in names
    assert "offboarding_employee" in names


def test_skills_readme_loads():
    repo_root = Path(__file__).resolve().parents[1]
    registry = SkillRegistry(repo_root / "agent_workspace" / "skills")
    readme = registry.read_skills_readme()
    assert "Supported Skills" in readme

