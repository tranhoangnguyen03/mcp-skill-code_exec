from pathlib import Path

from agent_workspace.hr_agent_v2.mcp_docs_registry import MCPDocsRegistry


def test_mcp_docs_registry_v2_renders_tools_and_examples():
    repo_root = Path(__file__).resolve().parents[1]
    v2_tools_root = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools"
    docs_dir = v2_tools_root / "mcp_docs"

    rendered = MCPDocsRegistry(docs_dir, tools_pythonpath=v2_tools_root).render_tool_contracts()
    assert "Tool: get_new_hires" in rendered
    assert "get_new_hires(" in rendered
    assert "import mcp_tools.bamboo_hr as bamboo_hr" in rendered
    assert "Examples" in rendered
