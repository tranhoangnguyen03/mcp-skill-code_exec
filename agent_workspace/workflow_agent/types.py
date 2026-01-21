from __future__ import annotations

from dataclasses import dataclass

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
