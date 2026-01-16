from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int


@dataclass(frozen=True)
class AgentResult:
    final_response: str
    plan_json: str | None = None
    generated_code: str | None = None
    exec_stdout: str | None = None
    exec_stderr: str | None = None
    attempts: int | None = None
