from pathlib import Path

from agent_workspace.workflow_agent.code_executor import PythonCodeExecutor


def test_code_executor_v2_imports_tools_from_v2_path():
    repo_root = Path(__file__).resolve().parents[1]
    workspace_dir = repo_root / "agent_workspace"
    tools_root = workspace_dir / "tools"

    executor = PythonCodeExecutor(workspace_dir, extra_pythonpaths=[tools_root])
    result = executor.run(
        """
import mcp_tools
import mcp_tools.bamboo_hr as bamboo

hires = bamboo.get_todays_hires()
print(mcp_tools.__file__)
print(len(hires))
"""
    )
    assert result.exit_code == 0
    normalized = result.stdout.replace("\\", "/")
    assert "agent_workspace/tools/mcp_tools" in normalized
    assert "\n3\n" in result.stdout or result.stdout.strip().endswith("3")
