"""WorkflowExecutor component for WorkflowAgent.

Manages the iterative lifecycle of code generation and execution.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Import from agent module (which re-exports from baml_bridge) to support
# test monkeypatching at the agent module level
from .. import agent as agent_module
from .._execution_result import ExecutionResult
from ..mcp_docs_registry import MCPDocsRegistry

if TYPE_CHECKING:
    from ..code_executor import PythonCodeExecutor as ExecutorType


# Regex patterns for continuation signal detection
CONTINUE_FACT_PATTERN = re.compile(r"CONTINUE_FACT:\s*(\w+)=(.+)")
CONTINUE_WORKFLOW_PATTERN = re.compile(r"CONTINUE_WORKFLOW:\s*(\w+)")


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


@dataclass
class MultiTurnExecuteResult:
    """Result of execution that may need continuation.

    Attributes:
        code: The generated and executed code
        exec_result: The execution result
        attempts_used: Number of attempts used
        needs_continuation: Whether this workflow needs another turn
        collected_facts: Key-value pairs extracted from CONTINUE_FACT signals
    """
    code: str
    exec_result: ExecutionResult
    attempts_used: int
    needs_continuation: bool = False
    collected_facts: dict[str, Any] = field(default_factory=dict)


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


def detect_continuation_signals(stdout: str) -> tuple[bool, dict[str, Any]]:
    """Detect continuation signals in execution stdout.

    Args:
        stdout: The standard output from execution

    Returns:
        Tuple of (needs_continuation, collected_facts)
    """
    needs_continuation = False
    collected_facts: dict[str, Any] = {}

    # Check for CONTINUE_FACT patterns
    for match in CONTINUE_FACT_PATTERN.finditer(stdout):
        key = match.group(1).strip()
        value = match.group(2).strip()
        collected_facts[key] = value

    # Check for CONTINUE_WORKFLOW pattern
    for match in CONTINUE_WORKFLOW_PATTERN.finditer(stdout):
        signal = match.group(1).strip().lower()
        if signal == "checkpoint_complete":
            needs_continuation = True

    return needs_continuation, collected_facts


class MultiTurnWorkflowExecutor:
    """Extended executor with multi-turn workflow support."""

    def __init__(self, executor: WorkflowExecutor):
        self._inner = executor

    def execute_with_continuation(
        self,
        user_message: str,
        plan_json: str,
        skill_md: str,
        *,
        conversation_history: str = "",
        workflow_state: dict | None = None,
    ) -> MultiTurnExecuteResult:
        """Execute workflow with multi-turn support.

        If the plan has requires_lookahead=true and a checkpoint step
        emits CONTINUE signals, this method returns a MultiTurnExecuteResult
        with needs_continuation=True and collected_facts.

        Args:
            user_message: The user's request
            plan_json: JSON string representation of the plan
            skill_md: The skill Markdown content
            conversation_history: Previous conversation context
            workflow_state: Optional existing workflow state to resume

        Returns:
            MultiTurnExecuteResult with continuation info if applicable
        """
        # Parse plan to check for multi-turn
        plan_data = json.loads(plan_json)
        is_multi_turn = plan_data.get("requires_lookahead", False)

        # Inject collected facts from previous turns into conversation history
        enriched_history = conversation_history
        if workflow_state and workflow_state.get("collected_facts"):
            facts_section = "## Collected Facts from Previous Steps\n"
            for key, value in workflow_state["collected_facts"].items():
                facts_section += f"- {key}: {value}\n"
            enriched_history = f"{facts_section}\n{conversation_history}"

        # Run standard execution
        result = self._inner.execute(
            user_message=user_message,
            plan_json=plan_json,
            skill_md=skill_md,
            conversation_history=enriched_history,
        )

        # Check for continuation signals
        needs_continuation, collected_facts = detect_continuation_signals(result.exec_result.stdout)

        return MultiTurnExecuteResult(
            code=result.code,
            exec_result=result.exec_result,
            attempts_used=result.attempts_used,
            needs_continuation=needs_continuation and is_multi_turn,
            collected_facts=collected_facts,
        )
