from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_workspace.workflow_agent.agent import WorkflowAgent, _extract_logic_flow_steps
from agent_workspace.workflow_agent.skill_registry import SkillRegistry


@dataclass(frozen=True)
class Scenario:
    name: str
    expected_action: str
    expected_skill: str | None
    expected_skill_group: str | None
    user_requests: list[str]
    required_code_patterns: list[str]
    required_log_patterns: list[str]
    required_response_keywords: list[str]


@dataclass(frozen=True)
class ScenarioRun:
    scenario: Scenario
    user_request: str
    plan: dict
    generated_code: str
    exec_stdout: str
    exec_stderr: str
    final_response: str


def list_scope_skills() -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[2]
    skills_dir = repo_root / "agent_workspace" / "skills_v2"
    registry = SkillRegistry(skills_dir)
    return {s.name: s.content for s in registry.list_skills()}


def run_scenario(*, scenario: Scenario, user_request: str) -> ScenarioRun:
    agent = WorkflowAgent()
    result = __import__("asyncio").run(agent.run(user_message=user_request))
    if result.plan_json is None:
        raise AssertionError("Expected plan_json to be set")
    plan = json.loads(result.plan_json)

    return ScenarioRun(
        scenario=scenario,
        user_request=user_request,
        plan=plan,
        generated_code=result.generated_code or "",
        exec_stdout=result.exec_stdout or "",
        exec_stderr=result.exec_stderr or "",
        final_response=result.final_response or "",
    )


def expected_logic_flow_steps(skill_name: str | None) -> list[str]:
    if not skill_name:
        return []
    skills = list_scope_skills()
    skill_md = skills.get(skill_name, "")
    return _extract_logic_flow_steps(skill_md)
