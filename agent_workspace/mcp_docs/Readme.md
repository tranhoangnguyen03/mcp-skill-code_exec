# MCP Docs

This folder documents the mock MCP tool servers under `agent_workspace/mcp_tools` using a consistent MCP-style tool schema.

## Structure

```
mcp_docs/
  <mcp>/
    server.json
    <tool>/
      tool.json
      examples.md
```

## Tool Schema

Each `tool.json` follows this shape:

- `name`: Tool name (string)
- `description`: What the tool does
- `inputSchema`: JSON Schema describing tool inputs (object)
- `outputSchema`: JSON Schema describing tool outputs
- `errors`: Common error cases and how they show up

