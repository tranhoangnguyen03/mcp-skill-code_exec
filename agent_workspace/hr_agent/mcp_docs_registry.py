from __future__ import annotations

import json
import re
from importlib import import_module
from inspect import signature
from pathlib import Path


class MCPDocsRegistry:
    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir

    def render_tool_contracts(self) -> str:
        if not self.docs_dir.exists():
            return ""

        parts: list[str] = []
        for mcp_dir in sorted([p for p in self.docs_dir.iterdir() if p.is_dir()]):
            server_path = mcp_dir / "server.json"
            server_json = {}
            if server_path.exists():
                server_json = json.loads(server_path.read_text(encoding="utf-8"))
            parts.append(f"# {mcp_dir.name}")
            if server_json:
                parts.append("## Server")
                parts.append("```json\n" + json.dumps(server_json, indent=2, ensure_ascii=False) + "\n```")

            tool_dirs = sorted([p for p in mcp_dir.iterdir() if p.is_dir()])
            for tool_dir in tool_dirs:
                parts.append(f"## Tool: {tool_dir.name}")
                parts.append(self._render_tool_block(tool_dir=tool_dir, server_json=server_json))

        return "\n\n".join(parts).strip()

    def _render_tool_block(self, *, tool_dir: Path, server_json: dict) -> str:
        tool_name = tool_dir.name

        python_module = server_json.get("python_module") if isinstance(server_json, dict) else None
        tools = server_json.get("tools") if isinstance(server_json, dict) else None

        if isinstance(python_module, str) and isinstance(tools, list) and tool_name in set(map(str, tools)):
            try:
                module = import_module(python_module)
                fn = getattr(module, tool_name, None)
            except Exception:
                fn = None
        else:
            fn = None

        lines: list[str] = []
        if fn is not None:
            try:
                sig = str(signature(fn))
            except Exception:
                sig = "(...)"
            lines.append("```python")
            lines.append(f"{tool_name}{sig}")
            lines.append("```")

        examples_path = tool_dir / "examples.md"
        if examples_path.exists():
            examples_md = examples_path.read_text(encoding="utf-8")
            python_blocks = _extract_fenced_blocks(examples_md, lang="python")
            if python_blocks:
                lines.append("### Examples")
                for block in python_blocks:
                    lines.append("```python")
                    lines.append(block.rstrip())
                    lines.append("```")

        return "\n".join(lines).strip()


def _extract_fenced_blocks(text: str, *, lang: str) -> list[str]:
    pattern = re.compile(rf"```{re.escape(lang)}\s*\n(.*?)\n```", re.DOTALL)
    return [m.group(1) for m in pattern.finditer(text)]
