from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .types import ExecutionResult


class PythonCodeExecutor:
    def __init__(self, workspace_dir: Path, timeout_seconds: int = 20):
        self.workspace_dir = workspace_dir
        self.timeout_seconds = timeout_seconds

    def run(self, code: str) -> ExecutionResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "generated.py"
            tmp_path.write_text(code, encoding="utf-8")

            env = dict(os.environ)
            pythonpath = str(self.workspace_dir)
            env["PYTHONPATH"] = (
                f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
                if env.get("PYTHONPATH")
                else pythonpath
            )

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
