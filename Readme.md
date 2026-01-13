## mcp-skill-code_exec

Demo “skill-driven” agent that:
- Scans `agent_workspace/skills/` to discover supported HR workflows
- Uses an OpenRouter LLM to pick a skill, generate Python code, execute it, then summarize results
- Provides mock “MCP tools” for BambooHR, Jira, and Slack under `agent_workspace/mcp_tools/`

### Folder Layout

```
agent_workspace/
  hr_agent/                Agent logic (planner → codegen → execute → respond)
  mcp_tools/               Mock integrations (bamboo_hr, jira, slack)
  prompts/                 Prompts (plan, codegen, respond)
  skills/                  Skill manuals (SKILL.md per skill)
  .env                     OpenRouter config (not committed)
```

### Setup

1) Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Ensure `agent_workspace/.env` contains:
- `open_router_api_key`
- `open_router_model_name`

### Run (CLI)

```bash
cd agent_workspace
python main_agent.py
```

### Run (Chat UI with Chainlit)

From the repo root:

```bash
chainlit run chainlit_app.py
```

### Skills

See the supported skills list in `agent_workspace/skills/Readme.md`.

### Tests

```bash
pytest
```
