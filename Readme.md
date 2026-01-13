# mcp-skill-code_exec

Skill-driven HR automation agent that:
- selects a scripted workflow when it matches a known skill
- otherwise generates a custom Python script using the available MCP tools
- executes the script and summarizes outputs

This repo includes mock integrations for BambooHR, Jira, and Slack under `agent_workspace/mcp_tools/`.

## How it works

- **Plan**: classify the request as `chat`, `execute_skill`, or `custom_script`
- **Codegen**: generate a runnable Python script using either:
  - a specific `SKILL.md` manual (scripted skills), or
  - a generic custom workflow manual (no skill match)
- **Execute**: run the generated code in a sandboxed subprocess with a timeout
- **Respond**: summarize stdout/stderr and the outcome

## Repository layout

```
agent_workspace/
  hr_agent/                Agent logic (plan → codegen → execute → respond)
  mcp_tools/               Mock integrations (bamboo_hr, jira, slack)
  mcp_docs/                MCP-style tool documentation (schemas + examples)
  prompts/                 Prompts (plan, codegen, respond, custom_skill)
  skills/                  Skill manuals (SKILL.md per skill)
  .env                     Local OpenRouter config (do not commit)
tests/                     Unit tests
```

## Setup

### Requirements

- Python 3.11+ recommended

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure OpenRouter

Copy the example env file and fill in values:

```bash
cp agent_workspace/.env.example agent_workspace/.env
```

`agent_workspace/.env` should contain:

```
open_router_api_key=...
open_router_model_name=...
```

## Run

### CLI

```bash
cd agent_workspace
python main_agent.py
```

### Chat UI (Chainlit)

```bash
chainlit run chainlit_app.py
```

## Skills and tools

- Skills list: `agent_workspace/skills/Readme.md`
- MCP tool docs (schemas): `agent_workspace/mcp_docs/`

## Tests

```bash
python -m pytest -q
```

## Notes for public sharing

- Do not commit `agent_workspace/.env` or any API keys.
- Chainlit creates local state under `.chainlit/` and `agent_workspace/.chainlit/` which should remain untracked.
