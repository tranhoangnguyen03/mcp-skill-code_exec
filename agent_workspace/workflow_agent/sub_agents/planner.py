"""Planner component for WorkflowAgent.

Encapsulates intent analysis, skill matching, and plan creation.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

# Import from agent module (which re-exports from baml_bridge) to support
# test monkeypatching at the agent module level
from .. import agent as agent_module
from ..skill_registry import Skill, SkillRegistry

if TYPE_CHECKING:
    from ..skill_registry import SkillRegistry as SkillRegistryType


@dataclass(frozen=True)
class Plan:
    """Represents a workflow plan.

    Attributes:
        action: One of "chat", "execute_skill", "custom_script"
        skill_group: The skill group directory name (e.g., "HR-scopes")
        skill_name: The skill name for execution
        intent: Human-readable description of what to do
        steps: List of logic flow steps from skill MD or LLM
        requires_lookahead: Whether this plan needs external data lookup before execution
        checkpoints: Steps that produce facts for downstream use
    """
    action: str
    skill_group: str | None
    skill_name: str | None
    intent: str
    steps: list[str]
    requires_lookahead: bool = False
    checkpoints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlanningResult:
    """Result of the planning phase.

    Attributes:
        plan: The Plan object
        plan_json: JSON string representation of the plan
        selected_skill: The matched Skill object (None for chat/custom_script)
    """
    plan: Plan
    plan_json: str
    selected_skill: Skill | None


class Planner:
    """Handles intent analysis, skill matching, and plan creation."""

    def __init__(self, skill_registry: SkillRegistryType):
        self._registry = skill_registry

    def plan(
        self,
        user_message: str,
        *,
        conversation_history: str = "",
        enable_review: bool = False,
    ) -> PlanningResult:
        """Create a plan from user message.

        Args:
            user_message: The user's request
            conversation_history: Previous conversation context
            enable_review: Whether to enable plan review step

        Returns:
            PlanningResult with plan, JSON, and selected skill
        """
        skills_readme = self._registry.read_skills_readme()
        skills = self._registry.list_skills()
        skill_groups = self._registry.list_skill_groups()

        plan_data = agent_module.workflow_plan(
            user_message=user_message,
            skills_readme=skills_readme,
            skill_names=[s.name for s in skills],
            skill_groups=skill_groups,
            conversation_history=conversation_history,
        )

        plan = _plan_from_dict(plan_data, skills)
        selected_skill: Skill | None = None

        if plan.action == "execute_skill" and plan.skill_name:
            selected_skill = _find_skill_by_name(plan.skill_name, skills)
            if selected_skill:
                skill_group = selected_skill.group
                skill_steps = selected_skill.logic_flow_steps
                plan = Plan(
                    action=plan.action,
                    skill_group=skill_group,
                    skill_name=plan.skill_name,
                    intent=plan.intent,
                    steps=skill_steps or plan.steps,
                    requires_lookahead=plan.requires_lookahead,
                    checkpoints=plan.checkpoints,
                )

        proposed_plan_json = _plan_to_json(plan)

        if selected_skill is not None and enable_review:
            reviewed_plan_data = agent_module.workflow_plan_review(
                user_message=user_message,
                proposed_plan_json=proposed_plan_json,
                selected_skill_md=selected_skill.content,
                conversation_history=conversation_history,
            )
            reviewed_plan = _plan_from_dict(reviewed_plan_data, skills)
            if reviewed_plan.action != "execute_skill":
                plan = reviewed_plan
                selected_skill = None
            else:
                plan = reviewed_plan
                selected_skill = _find_skill_by_name(plan.skill_name, skills)
                if selected_skill:
                    skill_group = selected_skill.group
                    skill_steps = selected_skill.logic_flow_steps
                    plan = Plan(
                        action=plan.action,
                        skill_group=skill_group,
                        skill_name=plan.skill_name,
                        intent=plan.intent,
                        steps=skill_steps or plan.steps,
                        requires_lookahead=plan.requires_lookahead,
                        checkpoints=plan.checkpoints,
                    )

        plan_json = _plan_to_json(plan)

        if plan.action in {"chat", "custom_script"}:
            return PlanningResult(plan=plan, plan_json=plan_json, selected_skill=None)

        return PlanningResult(plan=plan, plan_json=plan_json, selected_skill=selected_skill)


def _find_skill_by_name(skill_name: str, skills: list[Skill]) -> Skill | None:
    """Find a skill by name with fuzzy matching."""
    available = [s.name for s in skills]
    if skill_name in set(available):
        return next(s for s in skills if s.name == skill_name)

    normalized_available = {_normalize_skill_name(name): name for name in available}
    normalized = _normalize_skill_name(skill_name)

    mapped = normalized_available.get(normalized)
    if mapped:
        return next(s for s in skills if s.name == mapped)

    if len(available) == 1:
        return skills[0]

    return None


def _plan_from_dict(data: dict, skills: list[Skill]) -> Plan:
    """Create a Plan from dictionary data."""
    action = str(data.get("action") or "").strip()
    if action not in {"chat", "execute_skill", "custom_script"}:
        raise ValueError(f"Unknown action: {action}")

    skill_name = data.get("skill_name")
    if action == "execute_skill":
        if not isinstance(skill_name, str) or not skill_name.strip():
            raise ValueError("Missing skill_name for execute_skill")
        skill_name = skill_name.strip()
        available = [s.name for s in skills]
        if skill_name not in set(available):
            normalized_available = {_normalize_skill_name(name): name for name in available}
            normalized = _normalize_skill_name(skill_name)

            mapped = normalized_available.get(normalized)
            if mapped:
                skill_name = mapped
            elif len(available) == 1:
                skill_name = available[0]
            else:
                action = "custom_script"
                skill_name = _safe_custom_skill_name(skill_name)
    else:
        if action == "custom_script":
            skill_name = _safe_custom_skill_name(skill_name)
        else:
            skill_name = None

    intent = str(data.get("intent", ""))
    steps = [str(s) for s in (data.get("steps") or [])]
    skill_group = data.get("skill_group") if action in {"execute_skill", "custom_script"} else None
    if action in {"execute_skill", "custom_script"}:
        if not isinstance(skill_group, str) or not skill_group.strip():
            skill_group = None
        else:
            skill_group = skill_group.strip()

    # Multi-turn fields
    requires_lookahead = bool(data.get("requires_lookahead", False))
    checkpoints = [str(c) for c in (data.get("checkpoints") or [])]

    return Plan(
        action=action,
        skill_group=skill_group,
        skill_name=skill_name,
        intent=intent,
        steps=steps,
        requires_lookahead=requires_lookahead,
        checkpoints=checkpoints,
    )


def _plan_to_json(plan: Plan) -> str:
    """Convert a Plan to JSON string."""
    return json.dumps(
        {
            "action": plan.action,
            "skill_group": plan.skill_group,
            "skill_name": plan.skill_name,
            "intent": plan.intent,
            "steps": plan.steps,
            "requires_lookahead": plan.requires_lookahead,
            "checkpoints": plan.checkpoints,
        },
        indent=2,
        ensure_ascii=False,
    )


def _safe_custom_skill_name(value) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value.strip())
    if not cleaned:
        return None
    return cleaned[:80]


def _normalize_skill_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())
