import json
import sys
from importlib import import_module
from pathlib import Path

from agent_workspace.workflow_agent.mcp_docs_registry import MCPDocsRegistry


def test_mcp_docs_registry_v2_renders_tools_and_examples():
    repo_root = Path(__file__).resolve().parents[1]
    tools_root = repo_root / "agent_workspace" / "tools"
    docs_dir = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools" / "mcp_docs"

    rendered = MCPDocsRegistry(docs_dir, tools_pythonpath=tools_root).render_tool_contracts()
    assert "Tool: get_new_hires" in rendered
    assert "get_new_hires(" in rendered
    assert "import mcp_tools.bamboo_hr as bamboo_hr" in rendered
    assert "Examples" in rendered


def test_mcp_docs_registry_v2_renders_recruitment_scope_docs():
    repo_root = Path(__file__).resolve().parents[1]
    shared_tools_root = repo_root / "agent_workspace" / "tools"
    docs_dir = repo_root / "agent_workspace" / "skills_v2" / "Recruitment-scopes" / "tools" / "mcp_docs"

    rendered = MCPDocsRegistry(docs_dir, tools_pythonpath=shared_tools_root).render_tool_contracts()
    assert "# jira" in rendered
    assert "# slack" in rendered
    assert "# google_calendar" in rendered
    assert "Tool: create_ticket" in rendered
    assert "Tool: create_event" in rendered
    assert "# bamboo_hr" not in rendered


def test_mcp_docs_registry_v2_renders_procurement_scope_docs():
    repo_root = Path(__file__).resolve().parents[1]
    shared_tools_root = repo_root / "agent_workspace" / "tools"
    docs_dir = repo_root / "agent_workspace" / "skills_v2" / "Procurement-scopes" / "tools" / "mcp_docs"

    rendered = MCPDocsRegistry(docs_dir, tools_pythonpath=shared_tools_root).render_tool_contracts()
    assert "# jira" in rendered
    assert "# slack" in rendered
    assert "# google_calendar" in rendered
    assert "Tool: create_ticket" in rendered
    assert "Tool: create_event" in rendered
    assert "# bamboo_hr" not in rendered


def test_all_scopes_have_valid_mcp_docs_and_importable_tools():
    repo_root = Path(__file__).resolve().parents[1]
    skills_root = repo_root / "agent_workspace" / "skills_v2"
    tools_root = repo_root / "agent_workspace" / "tools"

    sys.path.insert(0, str(tools_root))
    try:
        scope_dirs = [p for p in skills_root.iterdir() if p.is_dir() and p.name.endswith("-scopes")]
        assert scope_dirs, "Expected at least one *-scopes directory under skills_v2"

        for scope_dir in scope_dirs:
            docs_dir = scope_dir / "tools" / "mcp_docs"
            assert docs_dir.exists(), f"Missing mcp_docs for scope {scope_dir.name}"

            for mcp_dir in [p for p in docs_dir.iterdir() if p.is_dir()]:
                server_path = mcp_dir / "server.json"
                assert server_path.exists(), f"Missing server.json for {scope_dir.name}/{mcp_dir.name}"
                server = json.loads(server_path.read_text(encoding="utf-8"))

                python_module = server.get("python_module") if isinstance(server, dict) else None
                if isinstance(python_module, str) and python_module.strip():
                    module_name = python_module.strip()
                else:
                    module_name = f"mcp_tools.{mcp_dir.name}"

                module = import_module(module_name)

                tools_list = server.get("tools") if isinstance(server, dict) else None
                assert isinstance(tools_list, list) and tools_list, f"Missing tools list in {server_path}"

                for tool_name in tools_list:
                    fn = getattr(module, str(tool_name), None)
                    assert callable(fn), f"Tool {module_name}.{tool_name} is not importable/callable"
    finally:
        try:
            sys.path.remove(str(tools_root))
        except ValueError:
            pass
