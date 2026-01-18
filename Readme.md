# mcp-skill-code_exec

Skill-driven HR automation agent that:
- selects a scripted workflow when it matches a known skill
- otherwise generates a custom Python script using the available MCP tools
- executes the script and summarizes outputs

This repo includes mock integrations for BambooHR, Jira, and Slack under `agent_workspace/skills_v2/HR-scopes/tools/mcp_tools/`.

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
  workflow_agent/          Agent logic (plan → codegen → execute → respond)
  prompts/                 Prompts (plan, codegen, respond, custom_skill)
  skills_v2/               Skill group and example manuals
    HR-scopes/
      examples/            Skill manuals (markdown examples)
      tools/
        mcp_tools/         Mock integrations (bamboo_hr, jira, slack)
        mcp_docs/          MCP-style tool documentation (server.json + examples)
    Recruitment-scopes/
      examples/            Skill manuals (markdown examples)
      tools/
        mcp_docs/          Scope-specific MCP docs (progressive disclosure)
    Procurement-scopes/
      examples/            Skill manuals (markdown examples)
      tools/
        mcp_docs/          Scope-specific MCP docs (progressive disclosure)
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
python agent_workspace/main.py
```

### Chat UI (Chainlit)

```bash
chainlit run chainlit_app_v2.py
```

## Skills and tools

- Skills list: [skills_v2/Readme.md](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/skills_v2/Readme.md)
- MCP tool docs (schemas): `agent_workspace/skills_v2/HR-scopes/tools/mcp_docs/`

## Supported Scopes & Suggested Queries

### HR-scopes
- "Onboard today’s new hires."
- "Onboard today’s new hires in Engineering only."
- "Offboard Maya Lopez effective today."
- "Review offboarding queue and create IT tickets."
- "Role change: update Charlie Davis to Senior DevOps Engineer and start access review."
- "Send probation check-in reminders for the 90-day window."
- "Set OOO calendar + auto-reply for alice@company.com next week and notify #engineering."
- "Kick off a Q4 performance review cycle and notify eligible employees."

### Recruitment-scopes
- "Schedule candidate interviews for candidate@example.com (Backend Engineer) with interviewer1@company.com and interviewer2@company.com 10–11am; notify #recruiting."
- "Chase interview feedback for candidate@example.com; remind U_ALICE and U_CHARLIE and post in #recruiting."

### Procurement-scopes
- "Create a purchase request: requester=Alice Chen, dept=Engineering, item=MacBook Pro, estimated cost=$2500. Notify #procurement."
- "Vendor onboarding request: vendor=Acme Security, requester_email=alice@company.com, kickoff 3:00–3:30pm, justification=security audit tool; notify #procurement."

### Custom / Tool-level
- "List all employees and group by department."
- "Search employees for ‘Engineering Manager’."
- "Who are today’s hires? Summarize names + managers."
- "Create two Jira tickets in IT and list open IT tickets."
- "Set Gmail auto responder for bob@company.com, then fetch it."
- "Create a calendar event for alice@company.com and then list her events for that date."

## Tests

```bash
python -m pytest -q
```

## Notes for public sharing

- Do not commit `agent_workspace/.env` or any API keys.
- Chainlit creates local state under `.chainlit/` and `agent_workspace/.chainlit/` which should remain untracked.
