## Why Those Scopes Don’t Have `tools/` Today
- The current agent is hard-wired to load MCP tool docs from `skills_v2/HR-scopes/tools/mcp_docs` and to execute generated code with `skills_v2/HR-scopes/tools` on `PYTHONPATH` (so `import mcp_tools.*` works).
- When we added Recruitment/Procurement, we kept tools centralized to avoid multiple `mcp_tools` packages on the import path (Python would pick the first one, causing fragile behavior).
- You’re right about Progressive Disclosure: the clean way is per-scope *documentation* (and optionally per-scope tool code later), while still letting overlapping tools share implementations.

## Goals
- Give `Recruitment-scopes/` and `Procurement-scopes/` their own `tools/mcp_docs` so codegen can be scope-specific (Progressive Disclosure).
- Refactor agent to select tool docs based on the selected skill’s `skill_group`.
- Rename `agent_workspace/hr_agent_v2` → `agent_workspace/workflow_agent`.
- Rename `agent_workspace/main_agent_v2.py` → `agent_workspace/main.py`.
- Propagate changes through code/tests/docs and verify with pytest.

## Tool Docs Per Scope (Progressive Disclosure)
- Create:
  - `skills_v2/Recruitment-scopes/tools/mcp_docs/`
  - `skills_v2/Procurement-scopes/tools/mcp_docs/`
- Populate only the tools/functions those scopes should “see” during codegen:
  - Recruitment: `jira.create_ticket`, `slack.send_dm`, `slack.post_message`, `google_calendar.create_event`
  - Procurement: `jira.create_ticket`, `slack.post_message`, `google_calendar.create_event` (for vendor kickoff)
- Keep tool *implementations* shared (still under `HR-scopes/tools/mcp_tools`) initially.
  - Agent will render Recruitment/Procurement docs while importing tool signatures from the shared tools pythonpath.
  - This enables Progressive Disclosure without duplicating runtime code.

## Agent Refactor: Select Docs By Scope
- Update the agent so tool contracts are chosen like:
  - If executing a skill: load docs from `skills_v2/{skill_group}/tools/mcp_docs`
  - If custom_script/chat: fall back to a “default” docs set (initially HR-scopes) or optionally union of all docs (we’ll pick the safer default to avoid prompt bloat).
- Keep execution `PYTHONPATH` including the shared tools root so generated code still runs.

## Renames (with Compatibility Strategy)
- Rename package directory:
  - `agent_workspace/hr_agent_v2/` → `agent_workspace/workflow_agent/`
- Update all imports across:
  - `tests/`, `chainlit_app_v2.py`, `agent_workspace/main.py`, and any internal modules.
- Optional (recommended) shims to avoid breaking any external references:
  - Keep `agent_workspace/hr_agent_v2/__init__.py` (and minimal modules if needed) as a thin re-export layer pointing to `workflow_agent`. This keeps older import paths working while the repo migrates.
- Rename entrypoint:
  - `agent_workspace/main_agent_v2.py` → `agent_workspace/main.py`
  - Update `tests/test_main_agent_v2.py` accordingly (and README run instructions).

## Tests (2 Tiers)
### Tier 1: Unit tests
- Add unit tests that:
  - Ensure per-scope docs directories exist and `MCPDocsRegistry` can render them when pointed at those docs dirs.
  - Ensure the agent chooses the correct docs set for `skill_group` (can be verified by checking the rendered contract text contains only the expected tools).

### Tier 2: Scenario tests (LLM-as-judge)
- Ensure the existing scenario suite still runs.
- Add/adjust scenarios so Recruitment/Procurement skills:
  - Produce `plan_json.skill_group` correctly
  - Generate code consistent with the now-scope-specific tool contracts
  - Continue to pass HeuristicJudge by default
  - Continue to be eligible for OpenRouterJudge when env vars are set

## Verification
- Run `pytest -q` and ensure all tests pass after renames + doc changes.
- Confirm `chainlit_app_v2` import test still passes.

## Files Expected To Change / Add
- Add:
  - `agent_workspace/skills_v2/Recruitment-scopes/tools/mcp_docs/...`
  - `agent_workspace/skills_v2/Procurement-scopes/tools/mcp_docs/...`
- Modify:
  - Agent module(s) to select docs per scope
  - Imports across repo due to rename (`workflow_agent`, `main.py`)
  - README run instructions
  - Tests that reference old names/paths