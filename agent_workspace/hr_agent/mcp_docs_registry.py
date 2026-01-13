from __future__ import annotations

import json
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
                tool_path = tool_dir / "tool.json"
                if not tool_path.exists():
                    continue
                tool_json = json.loads(tool_path.read_text(encoding="utf-8"))
                parts.append(f"## Tool: {tool_dir.name}")
                parts.append("```json\n" + json.dumps(tool_json, indent=2, ensure_ascii=False) + "\n```")

        return "\n\n".join(parts).strip()

