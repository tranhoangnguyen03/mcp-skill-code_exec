import inspect
import json
from pathlib import Path

from agent_workspace.mcp_tools import bamboo_hr, jira, slack


def _public_functions(module):
    funcs = []
    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if fn.__module__ != module.__name__:
            continue
        if name.startswith("_"):
            continue
        funcs.append(name)
    return sorted(funcs)


def test_mcp_docs_cover_all_tools():
    repo_root = Path(__file__).resolve().parents[1]
    docs_root = repo_root / "agent_workspace" / "mcp_docs"

    module_map = {
        "bamboo_hr": bamboo_hr,
        "jira": jira,
        "slack": slack,
    }

    for doc_name, module in module_map.items():
        server_path = docs_root / doc_name / "server.json"
        assert server_path.exists()
        server = json.loads(server_path.read_text(encoding="utf-8"))
        server_tools = set(server.get("tools", []))

        for fn_name in _public_functions(module):
            tool_dir = docs_root / doc_name / fn_name
            assert (tool_dir / "tool.json").exists()
            assert (tool_dir / "examples.md").exists()
            assert fn_name in server_tools

