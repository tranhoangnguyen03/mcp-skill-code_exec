import inspect
import json
import sys
from contextlib import contextmanager
from pathlib import Path


def _public_functions(module):
    funcs = []
    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if fn.__module__ != module.__name__:
            continue
        if name.startswith("_"):
            continue
        funcs.append(name)
    return sorted(funcs)


@contextmanager
def _sys_path(path: Path):
    p = str(path)
    sys.path.insert(0, p)
    try:
        yield
    finally:
        try:
            sys.path.remove(p)
        except ValueError:
            pass


def test_mcp_docs_v2_cover_all_tools_and_have_examples():
    repo_root = Path(__file__).resolve().parents[1]
    tools_root = repo_root / "agent_workspace" / "tools"
    docs_root = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools" / "mcp_docs"

    with _sys_path(tools_root):
        from mcp_tools import bamboo_hr, jira, slack

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
                assert (tool_dir / "examples.md").exists()
                assert fn_name in server_tools
