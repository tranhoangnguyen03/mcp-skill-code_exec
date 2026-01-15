from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .types import ExecutionResult


class PythonCodeExecutor:
    def __init__(
        self,
        workspace_dir: Path,
        *,
        timeout_seconds: int = 20,
        extra_pythonpaths: list[Path] | None = None,
    ):
        self.workspace_dir = workspace_dir
        self.timeout_seconds = timeout_seconds
        self.extra_pythonpaths = [p for p in (extra_pythonpaths or []) if p]

    def run(self, code: str) -> ExecutionResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "generated.py"
            tmp_path.write_text(code, encoding="utf-8")

            env = dict(os.environ)
            pythonpaths: list[str] = [str(p) for p in self.extra_pythonpaths] + [str(self.workspace_dir)]
            existing = env.get("PYTHONPATH")
            if existing:
                pythonpaths.append(existing)
            env["PYTHONPATH"] = os.pathsep.join(pythonpaths)

            try:
                proc = subprocess.run(
                    [sys.executable, str(tmp_path)],
                    cwd=str(self.workspace_dir),
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                )
                return ExecutionResult(
                    stdout=proc.stdout or "",
                    stderr=proc.stderr or "",
                    exit_code=int(proc.returncode),
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    stdout="",
                    stderr=f"Execution timed out after {self.timeout_seconds}s",
                    exit_code=124,
                )
