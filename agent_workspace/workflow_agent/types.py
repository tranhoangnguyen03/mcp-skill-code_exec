from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Re-export ExecutionResult from _execution_result for backward compatibility
from ._execution_result import ExecutionResult as ExecutionResultFromExecutor


# Keep ExecutionResult name for backward compatibility
ExecutionResult = ExecutionResultFromExecutor


@dataclass(frozen=True)
class AgentResult:
    final_response: str
    plan_json: str | None = None
    generated_code: str | None = None
    exec_stdout: str | None = None
    exec_stderr: str | None = None
    attempts: int | None = None


@dataclass
class WorkflowState:
    """Tracks state for multi-turn workflows.

    Attributes:
        workflow_id: Unique identifier for this workflow instance
        session_id: The session/thread ID this workflow belongs to
        current_step: The current step index in the workflow
        plan_json: The original plan JSON for this workflow
        collected_facts: Key-value pairs discovered during checkpoint steps
        checkpoint_results: Raw results from each checkpoint for debugging
        is_multi_turn: Whether this is a multi-turn workflow
        created_at: ISO timestamp of when the workflow was created
    """
    workflow_id: str
    session_id: str
    current_step: int = 0
    plan_json: str = ""
    collected_facts: dict[str, Any] = field(default_factory=dict)
    checkpoint_results: list[dict] = field(default_factory=list)
    is_multi_turn: bool = False
    created_at: str = ""


@dataclass
class WorkflowExecuteResult:
    """Result of workflow execution that may need continuation.

    Attributes:
        code: The generated and executed code
        exec_result: The execution result
        attempts_used: Number of attempts used
        needs_continuation: Whether this workflow needs another turn
        workflow_state: The updated workflow state (if multi-turn)
        continuation_facts: Facts extracted from this execution (for next turn)
    """
    code: str
    exec_result: ExecutionResult
    attempts_used: int
    needs_continuation: bool = False
    workflow_state: WorkflowState | None = None
    continuation_facts: dict[str, Any] = field(default_factory=dict)
