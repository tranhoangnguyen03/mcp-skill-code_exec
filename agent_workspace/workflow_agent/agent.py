from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from .baml_bridge import workflow_chat, workflow_codegen, workflow_plan, workflow_plan_review, workflow_respond
from .code_executor import PythonCodeExecutor
from .mcp_docs_registry import MCPDocsRegistry
from .skill_registry import SkillRegistry
from .types import AgentResult, ExecutionResult


@dataclass(frozen=True)
class Plan:
    action: str
    skill_group: str | None
    skill_name: str | None
    intent: str
    steps: list[str]


class WorkflowAgent:
    def __init__(self, max_attempts: int = 3, *, enable_workflow_plan_review: bool | None = None):
        self.max_attempts = max(1, int(max_attempts))
        self.workspace_dir = Path(__file__).resolve().parents[1]
        self.skills_v2_dir = self.workspace_dir / "skills_v2"
        self.skills = SkillRegistry(self.skills_v2_dir)

        self.default_tools_root = self.workspace_dir / "tools"
        self.default_docs_dir = self.skills_v2_dir / "HR-scopes" / "tools" / "mcp_docs"
        self.executor = PythonCodeExecutor(self.workspace_dir, extra_pythonpaths=[self.default_tools_root])
        self.custom_skill_md_path = self.skills_v2_dir / "custom_skill.md"
        if enable_workflow_plan_review is None:
            enable_workflow_plan_review = _env_bool("enable_workflow_plan_review", default=False)
        self.enable_workflow_plan_review = bool(enable_workflow_plan_review)

    async def run(self, user_message: str) -> AgentResult:
        plan, plan_json, selected_skill = self.plan(user_message=user_message)
        if plan.action == "chat":
            final_response = self.chat(user_message=user_message)
            return AgentResult(final_response=final_response.strip(), plan_json=plan_json)

        skill_md = self.get_skill_md(plan=plan, selected_skill=selected_skill)
        code, exec_result, attempts_used = self.generate_and_execute_with_retries(
            user_message=user_message,
            plan_json=plan_json,
            skill_md=skill_md,
        )
        final_response = self.respond(
            user_message=user_message,
            plan_json=plan_json,
            executed_code=code,
            exec_result=exec_result,
            attempts=attempts_used,
        )

        return AgentResult(
            final_response=final_response.strip(),
            plan_json=plan_json,
            generated_code=code,
            exec_stdout=exec_result.stdout,
            exec_stderr=exec_result.stderr,
            attempts=attempts_used,
        )

    def plan(self, user_message: str):
        skills_readme = self.skills.read_skills_readme()
        skills = self.skills.list_skills()
        skill_groups = self.skills.list_skill_groups()
        plan_data = workflow_plan(
            user_message=user_message,
            skills_readme=skills_readme,
            skill_names=[s.name for s in skills],
            skill_groups=skill_groups,
        )
        plan = _plan_from_dict(plan_data, skills)
        selected_skill = None
        if plan.action == "execute_skill" and plan.skill_name:
            selected_skill = next(s for s in skills if s.name == plan.skill_name)
            skill_group = _infer_skill_group(selected_skill.path)
            skill_steps = _extract_logic_flow_steps(selected_skill.content)
            plan = Plan(
                action=plan.action,
                skill_group=skill_group,
                skill_name=plan.skill_name,
                intent=plan.intent,
                steps=skill_steps or plan.steps,
            )

        proposed_plan_json = json.dumps(
            {
                "action": plan.action,
                "skill_group": plan.skill_group,
                "skill_name": plan.skill_name,
                "intent": plan.intent,
                "steps": plan.steps,
            },
            indent=2,
            ensure_ascii=False,
        )

        if selected_skill is not None and self.enable_workflow_plan_review:
            reviewed_plan_data = workflow_plan_review(
                user_message=user_message,
                proposed_plan_json=proposed_plan_json,
                selected_skill_md=selected_skill.content,
            )
            reviewed_plan = _plan_from_dict(reviewed_plan_data, skills)
            if reviewed_plan.action != "execute_skill":
                plan = reviewed_plan
                selected_skill = None
            else:
                plan = reviewed_plan
                selected_skill = next(s for s in skills if s.name == plan.skill_name)
                skill_group = _infer_skill_group(selected_skill.path)
                skill_steps = _extract_logic_flow_steps(selected_skill.content)
                plan = Plan(
                    action=plan.action,
                    skill_group=skill_group,
                    skill_name=plan.skill_name,
                    intent=plan.intent,
                    steps=skill_steps or plan.steps,
                )

        plan_json = json.dumps(
            {
                "action": plan.action,
                "skill_group": plan.skill_group,
                "skill_name": plan.skill_name,
                "intent": plan.intent,
                "steps": plan.steps,
            },
            indent=2,
            ensure_ascii=False,
        )

        if plan.action in {"chat", "custom_script"}:
            return plan, plan_json, None

        return plan, plan_json, selected_skill

    def codegen(
        self,
        user_message: str,
        plan_json: str,
        skill_md: str,
        *,
        attempt: int = 1,
        previous_error: str = "",
        previous_code: str = "",
    ) -> str:
        tool_contracts = self._docs_registry_for_plan(plan_json=plan_json).render_tool_contracts()
        code = workflow_codegen(
            user_message=user_message,
            plan_json=plan_json,
            skill_md=skill_md,
            tool_contracts=tool_contracts,
            attempt=attempt,
            previous_error=previous_error,
            previous_code=previous_code,
        )
        extracted = _extract_code_block(code)
        compile(extracted, "<generated>", "exec")
        return extracted

    def execute(self, code: str, *, plan_json: str | None = None) -> ExecutionResult:
        tools_root = self._tools_root_for_plan(plan_json=plan_json)
        extra = [tools_root] if tools_root and tools_root != self.default_tools_root else None
        return self.executor.run(code, extra_pythonpaths=extra)

    def respond(
        self,
        user_message: str,
        plan_json: str,
        executed_code: str,
        exec_result: ExecutionResult,
        *,
        attempts: int,
    ) -> str:
        return workflow_respond(
            user_message=user_message,
            plan_json=plan_json,
            executed_code=executed_code,
            exec_stdout=exec_result.stdout,
            exec_stderr=exec_result.stderr,
            exit_code=exec_result.exit_code,
            attempts=attempts,
        )

    def chat(self, user_message: str) -> str:
        skills_readme = self.skills.read_skills_readme()
        custom_skill_md = self.custom_skill_md_path.read_text(encoding="utf-8")
        return workflow_chat(user_message=user_message, skills_readme=skills_readme, custom_skill_md=custom_skill_md)

    def get_skill_md(self, plan: Plan, selected_skill) -> str:
        if plan.action == "execute_skill":
            return selected_skill.content
        return self.custom_skill_md_path.read_text(encoding="utf-8")

    def generate_and_execute_with_retries(self, user_message: str, plan_json: str, skill_md: str):
        last_code = ""
        last_error = ""
        last_exec = ExecutionResult(stdout="", stderr="", exit_code=1)
        attempts_used = 0

        for attempt in range(1, self.max_attempts + 1):
            attempts_used = attempt
            try:
                code = self.codegen(
                    user_message=user_message,
                    plan_json=plan_json,
                    skill_md=skill_md,
                    attempt=attempt,
                    previous_error=last_error,
                    previous_code=last_code,
                )
            except Exception as e:
                last_code = last_code or ""
                last_error = f"Code generation failed: {e}"
                last_exec = ExecutionResult(stdout="", stderr=last_error, exit_code=1)
                continue

            last_code = code
            exec_result = self.execute(code=code, plan_json=plan_json)
            last_exec = exec_result
            if exec_result.exit_code == 0:
                return code, exec_result, attempts_used

            last_error = exec_result.stderr or f"Execution failed with exit_code={exec_result.exit_code}"

        return last_code, last_exec, attempts_used

    def _docs_registry_for_plan(self, *, plan_json: str) -> MCPDocsRegistry:
        docs_dir = self.default_docs_dir
        try:
            data = json.loads(plan_json)
        except Exception:
            data = {}
        group = data.get("skill_group") if isinstance(data, dict) else None
        if isinstance(group, str) and group.strip():
            group_tools_root = self.skills_v2_dir / group.strip() / "tools"
            group_docs_dir = group_tools_root / "mcp_docs"
            if group_docs_dir.exists():
                docs_dir = group_docs_dir
        return MCPDocsRegistry(docs_dir, tools_pythonpath=self.default_tools_root)

    def _tools_root_for_plan(self, *, plan_json: str | None) -> Path | None:
        return self.default_tools_root


def _parse_plan(plan_text: str, skills):
    cleaned = plan_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
    cleaned = cleaned.strip()
    data = json.loads(cleaned)
    return _plan_from_dict(data, skills)


def _plan_from_dict(data: dict, skills) -> Plan:
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

    return Plan(action=action, skill_group=skill_group, skill_name=skill_name, intent=intent, steps=steps)


def _safe_custom_skill_name(value) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value.strip())
    if not cleaned:
        return None
    return cleaned[:80]


def _normalize_skill_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def _infer_skill_group(skill_path: Path) -> str | None:
    parts = list(skill_path.parts)
    try:
        idx = parts.index("skills_v2")
    except ValueError:
        return None
    if idx + 1 >= len(parts):
        return None
    group = parts[idx + 1]
    return group or None


def _extract_logic_flow_steps(skill_md: str) -> list[str]:
    lines = skill_md.splitlines()
    start_idx = None
    for idx, line in enumerate(lines):
        if line.strip().lower() == "## logic flow":
            start_idx = idx + 1
            break
    if start_idx is None:
        return []

    steps: list[str] = []
    for line in lines[start_idx:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            steps.append(m.group(1).strip())

    return steps

def _extract_code_block(text: str) -> str:
    t = text.strip()
    if "```" not in t:
        return t
    parts = t.split("```")
    if len(parts) < 3:
        return t
    code = parts[1]
    if code.lstrip().startswith(("python\n", "py\n")):
        code = code.split("\n", 1)[1]
    return code.strip()


def _env_bool(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    cleaned = value.strip().lower()
    if not cleaned:
        return default
    if cleaned in {"1", "true", "yes", "y", "on"}:
        return True
    if cleaned in {"0", "false", "no", "n", "off"}:
        return False
    return default
