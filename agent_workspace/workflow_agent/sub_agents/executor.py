"""WorkflowExecutor component for WorkflowAgent.

Manages the iterative lifecycle of code generation and execution.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

# Import from agent module (which re-exports from baml_bridge) to support
# test monkeypatching at the agent module level
from .. import agent as agent_module
from .._execution_result import ExecutionResult
from ..mcp_docs_registry import MCPDocsRegistry

if TYPE_CHECKING:
    from ..code_executor import PythonCodeExecutor as ExecutorType


@dataclass(frozen=True)
class ExecuteResult:
    """Result of the execute phase.

    Attributes:
        code: The generated and executed code
        exec_result: The execution result
        attempts_used: Number of attempts used
    """
    code: str
    exec_result: ExecutionResult
    attempts_used: int


class WorkflowExecutor:
    """Handles code generation and execution with retry logic."""

    def __init__(
        self,
        executor: ExecutorType,
        skills_v2_dir: Path,
        default_tools_root: Path,
        default_docs_dir: Path,
        max_attempts: int = 3,
    ):
        self._executor = executor
        self._skills_v2_dir = skills_v2_dir
        self._default_tools_root = default_tools_root
        self._default_docs_dir = default_docs_dir
        self.max_attempts = max(1, int(max_attempts))

    def execute(
        self,
        user_message: str,
        plan_json: str,
        skill_md: str,
        *,
        conversation_history: str = "",
    ) -> ExecuteResult:
        """Execute the workflow with retries.

        Args:
            user_message: The user's request
            plan_json: JSON string representation of the plan
            skill_md: The skill Markdown content
            conversation_history: Previous conversation context

        Returns:
            ExecuteResult with code, execution result, and attempts used
        """
        last_code = ""
        last_error = ""
        last_exec = ExecutionResult(stdout="", stderr="", exit_code=1)
        attempts_used = 0

        for attempt in range(1, self.max_attempts + 1):
            attempts_used = attempt
            try:
                code = self._codegen(
                    user_message=user_message,
                    plan_json=plan_json,
                    skill_md=skill_md,
                    attempt=attempt,
                    previous_error=last_error,
                    previous_code=last_code,
                    conversation_history=conversation_history,
                )
            except Exception as e:
                last_code = last_code or ""
                last_error = f"Code generation failed: {e}"
                last_exec = ExecutionResult(stdout="", stderr=last_error, exit_code=1)
                continue

            last_code = code
            exec_result = self._execute(code=code, plan_json=plan_json)
            last_exec = exec_result
            if exec_result.exit_code == 0:
                return ExecuteResult(code=code, exec_result=exec_result, attempts_used=attempts_used)

            last_error = exec_result.stderr or f"Execution failed with exit_code={exec_result.exit_code}"

        return ExecuteResult(code=last_code, exec_result=last_exec, attempts_used=attempts_used)

    def _codegen(
        self,
        user_message: str,
        plan_json: str,
        skill_md: str,
        *,
        attempt: int,
        previous_error: str,
        previous_code: str,
        conversation_history: str,
    ) -> str:
        """Generate code using BAML."""
        docs_registry = self._docs_registry_for_plan(plan_json=plan_json)
        tool_contracts = docs_registry.render_tool_contracts()

        code = agent_module.workflow_codegen(
            user_message=user_message,
            plan_json=plan_json,
            skill_md=skill_md,
            tool_contracts=tool_contracts,
            attempt=attempt,
            previous_error=previous_error,
            previous_code=previous_code,
            conversation_history=conversation_history,
        )
        extracted = _extract_code_block(code)
        compile(extracted, "<generated>", "exec")
        return extracted

    def _execute(self, code: str, *, plan_json: str | None = None) -> ExecutionResult:
        """Execute code in subprocess."""
        tools_root = self._tools_root_for_plan(plan_json=plan_json)
        extra = [tools_root] if tools_root and tools_root != self._default_tools_root else None
        raw_result = self._executor.run(code, extra_pythonpaths=extra)
        return ExecutionResult(stdout=raw_result.stdout, stderr=raw_result.stderr, exit_code=raw_result.exit_code)

    def _docs_registry_for_plan(self, *, plan_json: str) -> MCPDocsRegistry:
        """Get the appropriate MCP docs registry for the plan."""
        docs_dir = self._default_docs_dir
        try:
            data = json.loads(plan_json)
        except Exception:
            data = {}
        group = data.get("skill_group") if isinstance(data, dict) else None
        if isinstance(group, str) and group.strip():
            group_tools_root = self._skills_v2_dir / group.strip() / "tools"
            group_docs_dir = group_tools_root / "mcp_docs"
            if group_docs_dir.exists():
                docs_dir = group_docs_dir
        return MCPDocsRegistry(docs_dir, tools_pythonpath=self._default_tools_root)

    def _tools_root_for_plan(self, *, plan_json: str | None) -> Path | None:
        """Get the tools root for the plan."""
        return self._default_tools_root

    def respond(
        self,
        user_message: str,
        plan_json: str,
        executed_code: str,
        exec_result: ExecutionResult,
        *,
        conversation_history: str = "",
        attempts: int,
    ) -> str:
        """Generate the final response after execution."""
        return agent_module.workflow_respond(
            user_message=user_message,
            plan_json=plan_json,
            executed_code=executed_code,
            exec_stdout=exec_result.stdout,
            exec_stderr=exec_result.stderr,
            exit_code=exec_result.exit_code,
            attempts=attempts,
            conversation_history=conversation_history,
        )


def _extract_code_block(text: str) -> str:
    """Extract Python code from markdown code fences."""
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
