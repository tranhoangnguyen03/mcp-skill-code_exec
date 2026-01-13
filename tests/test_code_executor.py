from pathlib import Path

from agent_workspace.hr_agent.code_executor import PythonCodeExecutor


def test_executor_runs_code_and_captures_stdout():
    repo_root = Path(__file__).resolve().parents[1]
    workspace = repo_root / "agent_workspace"
    ex = PythonCodeExecutor(workspace_dir=workspace, timeout_seconds=5)
    result = ex.run('print("hello")')
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello"

