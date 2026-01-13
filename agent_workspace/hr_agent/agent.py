from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .code_executor import PythonCodeExecutor
from .mcp_docs_registry import MCPDocsRegistry
from .openrouter_client import LLMMessage, OpenRouterClient
from .prompts import PromptStore
from .skill_registry import SkillRegistry
from .types import AgentResult, ExecutionResult


@dataclass(frozen=True)
class Plan:
    action: str
    skill_name: str | None
    intent: str
    steps: list[str]


class HRAgent:
    def __init__(self, llm: OpenRouterClient, max_attempts: int = 3):
        self.llm = llm
        self.max_attempts = max(1, int(max_attempts))
        self.workspace_dir = Path(__file__).resolve().parents[1]
        self.prompts = PromptStore(self.workspace_dir / "prompts")
        self.skills = SkillRegistry(self.workspace_dir / "skills")
        self.mcp_docs = MCPDocsRegistry(self.workspace_dir / "mcp_docs")
        self.executor = PythonCodeExecutor(self.workspace_dir)

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

        plan_prompt = self.prompts.load("plan.txt").format(
            user_message=user_message,
            skills_readme=skills_readme,
            skill_names=", ".join([s.name for s in skills]) or "(none)",
        )
        plan_text = self.llm.chat([LLMMessage(role="user", content=plan_prompt)], temperature=0.1)
        plan = _parse_plan(plan_text, skills)
        plan_json = json.dumps(
            {
                "action": plan.action,
                "skill_name": plan.skill_name,
                "intent": plan.intent,
                "steps": plan.steps,
            },
            indent=2,
            ensure_ascii=False,
        )

        if plan.action in {"chat", "custom_script"}:
            return plan, plan_json, None

        selected_skill = next(s for s in skills if s.name == plan.skill_name)
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
        tool_contracts = self.mcp_docs.render_tool_contracts()
        code_prompt = self.prompts.load("codegen.txt").format(
            user_message=user_message,
            plan_json=plan_json,
            skill_md=skill_md,
            tool_contracts=tool_contracts,
            attempt=attempt,
            previous_error=previous_error,
            previous_code=previous_code,
        )
        code = self.llm.chat([LLMMessage(role="user", content=code_prompt)], temperature=0.2)
        extracted = _extract_code_block(code)
        compile(extracted, "<generated>", "exec")
        return extracted

    def execute(self, code: str) -> ExecutionResult:
        return self.executor.run(code)

    def respond(
        self,
        user_message: str,
        plan_json: str,
        executed_code: str,
        exec_result: ExecutionResult,
        *,
        attempts: int,
    ) -> str:
        respond_prompt = self.prompts.load("respond.txt").format(
            user_message=user_message,
            plan_json=plan_json,
            executed_code=executed_code,
            exec_stdout=exec_result.stdout,
            exec_stderr=exec_result.stderr,
            exit_code=exec_result.exit_code,
            attempts=attempts,
        )
        return self.llm.chat([LLMMessage(role="user", content=respond_prompt)], temperature=0.2)

    def chat(self, user_message: str) -> str:
        prompt = self.prompts.load("chat.txt").format(user_message=user_message)
        return self.llm.chat([LLMMessage(role="user", content=prompt)], temperature=0.3)

    def get_skill_md(self, plan: Plan, selected_skill) -> str:
        if plan.action == "execute_skill":
            return selected_skill.content
        return self.prompts.load("custom_skill.txt")

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
            exec_result = self.execute(code=code)
            last_exec = exec_result
            if exec_result.exit_code == 0:
                return code, exec_result, attempts_used

            last_error = exec_result.stderr or f"Execution failed with exit_code={exec_result.exit_code}"

        return last_code, last_exec, attempts_used

def _parse_plan(plan_text: str, skills):
    cleaned = plan_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
    cleaned = cleaned.strip()
    data = json.loads(cleaned)

    action = str(data.get("action") or "").strip()
    if action not in {"chat", "execute_skill", "custom_script"}:
        raise ValueError(f"Unknown action: {action}")

    skill_name = data.get("skill_name")
    if action == "execute_skill":
        if not isinstance(skill_name, str) or not skill_name.strip():
            raise ValueError("Missing skill_name for execute_skill")
        skill_name = skill_name.strip()
        if skill_name not in {s.name for s in skills}:
            raise ValueError(f"Unknown skill_name: {skill_name}")
    else:
        skill_name = None

    intent = str(data.get("intent", ""))
    steps = [str(s) for s in (data.get("steps") or [])]
    return Plan(action=action, skill_name=skill_name, intent=intent, steps=steps)


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
