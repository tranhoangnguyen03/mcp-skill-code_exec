# Agent Workspace

This module implements a **Workflow Agent** capable of planning and executing complex tasks by generating and running Python code. It leverages a "Skill" system where workflows are defined in Markdown and an "MCP Tool" system for interacting with external services.

## Overview

The Workflow Agent follows a multi-step process for each user request:
1.  **Planning**: Determines if the request requires a specific skill, a custom script, or a simple chat response.
2.  **Code Generation**: Generates Python code based on the selected skill, available tool documentation (MCP docs), and the user's intent.
3.  **Execution**: Runs the generated code in a controlled environment with access to predefined tools.
4.  **Response Generation**: Summarizes the execution results and provides a final answer to the user.
5.  **Multi-turn Continuation**: If the plan requires lookahead, the agent collects facts, resumes codegen with those facts, and continues until completion.

## Key Components

### 1. Workflow Agent ([workflow_agent/](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/))
The core logic resides here:
- [agent.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py): The main `WorkflowAgent` class that orchestrates the entire lifecycle.
- [code_executor.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/code_executor.py): Handles the safe execution of generated Python code.
- [skill_registry.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/skill_registry.py): Manages the discovery and loading of skills from the `skills_v2` directory.
- [mcp_docs_registry.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/mcp_docs_registry.py): Manages documentation for MCP tools used during code generation.
- [baml_bridge.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/baml_bridge.py): Interface for LLM-powered planning and code generation.

### 2. Skills ([skills_v2/](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/skills_v2/))
Skills define the agent's capabilities. They are organized by "scopes" (e.g., HR, Recruitment, Procurement).
- **Examples**: Markdown files in `examples/` describe specific workflows and logic flows.
- **MCP Docs**: Documentation for tools available within each scope.

### 3. MCP Tools ([tools/mcp_tools/](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/tools/mcp_tools/))
Python implementations of tools that the agent can use in its generated code. Supported services include:
- BambooHR
- Jira
- Slack
- Google Calendar
- Gmail
- Lattice

### 4. Data & Memory
- [data/](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/data/): Contains mock JSON data for local development and testing of tools.
- [memory/](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/memory/): Stores session state and planning information.

## Getting Started

The entry point for the module is [main.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/main.py).

```python
from agent_workspace.workflow_agent.agent import WorkflowAgent
import asyncio

async def run():
    agent = WorkflowAgent()
    result = await agent.run("Run the Monday morning onboarding for engineers.")
    print(result.final_response)

if __name__ == "__main__":
    asyncio.run(run())
```

## Directory Structure

```text
agent_workspace/
├── data/               # Mock data for services
├── memory/             # Session and planning memory
├── skills_v2/          # Skill definitions and tool docs
├── tools/
│   └── mcp_tools/      # Python tool implementations
├── workflow_agent/     # Core agent logic and BAML bridge
└── main.py             # Entry point
```

## Multi-turn workflows
When a plan sets `requires_lookahead: true`, the agent:
- Runs checkpoint steps until it emits `CONTINUE_FACT` and `CONTINUE_WORKFLOW: checkpoint_complete`.
- Saves collected facts into workflow state.
- Resumes codegen with an injected facts section until a final response is produced.
