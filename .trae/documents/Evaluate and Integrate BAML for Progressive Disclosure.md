## Answer: Is skills_v2/Readme.md used for planning?
- Yes. The planner reads it via [SkillRegistry.read_skills_readme](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/skill_registry.py#L48-L55), and [HRAgent.plan](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py#L67-L76) injects it into the planning prompt.
- It should be updated if you want better planning. Right now it only lists skill groups and skill names ([skills_v2/Readme.md](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/skills_v2/Readme.md#L1-L26)); adding short “when to use this scope”, canonical skill names, and available tools improves scope routing and reduces misclassification.

## Fitness of BAML Proposal (Repo-Specific)
- **Planner**: best fit (replaces brittle JSON parsing in [_parse_plan](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py#L233-L277)).
- **Progressive disclosure**: strong fit (BAML functions can take structured tool contracts instead of markdown-only context).
- **Codegen**: good fit with your constraint (Option A). Keep generating Python as a string; move the prompt and schema to BAML for maintainability/validation.
- **OpenRouter**: compatible. BAML supports OpenRouter via `openai-generic` with `base_url=https://openrouter.ai/api/v1` (Boundary docs: https://docs.boundaryml.com/ref/llm-client-providers/openai-generic).

## Updated Implementation Plan (Includes adding mcp_tools for Recruitment/Procurement)
### 1) Add `mcp_tools` packages for Recruitment-scopes and Procurement-scopes
- Create `agent_workspace/skills_v2/Recruitment-scopes/tools/mcp_tools/` with `__init__.py`, `_data.py`, and the modules required by that scope’s `mcp_docs` (`candidate_tracker.py`, `google_calendar.py`, `jira.py`, `slack.py`).
- Create `agent_workspace/skills_v2/Procurement-scopes/tools/mcp_tools/` with `__init__.py`, `_data.py`, and the modules required by that scope’s `mcp_docs` (`google_calendar.py`, `jira.py`, `slack.py`).
- Reuse the same mock behaviors and seed data loading patterns as HR’s tools (e.g. copying/adapting [HR _data.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/skills_v2/HR-scopes/tools/mcp_tools/_data.py#L1-L39) and the relevant tool modules).
- Verify that with these folders present, execution can switch to per-scope tools via [_tools_root_for_plan](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py#L217-L230).

### 2) Update skills_v2/Readme.md to improve planning
- Keep the current skills list, but add:
  - One-paragraph “scope description” per group (HR vs Recruitment vs Procurement).
  - A short list of “available tool families” per scope (after step 1 this becomes true at runtime, not docs-only).
  - Ensure displayed skill names match the titles extracted from the example markdowns to reduce mismatch.

### 3) Add BAML prompt layer (no behavior change yet)
- Add a `baml/` (or `agent_workspace/baml/`) directory and define BAML functions mirroring existing prompt intents.
- Configure a BAML client using `openai-generic` targeting OpenRouter (base_url override).
- Add BAML runtime dependency and wire it into the Python project setup.

### 4) Migrate the planner to BAML (highest ROI)
- Replace the `plan.txt` + `_parse_plan` approach with a BAML `PlanRequest(...) -> Plan` function.
- Keep `plan_json` output shape identical so Chainlit UI and tests remain stable.
- Preserve existing “skill selection” post-processing (skill_group inference + logic-flow step override).

### 5) Migrate codegen to BAML (Option A)
- Implement BAML `GeneratePython(...) -> string` that outputs the Python code (still as a string).
- Preserve existing post-processing and safety checks:
  - [_extract_code_block](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py#L326-L336)
  - `compile()` check
  - Retry loop in [generate_and_execute_with_retries](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py#L167-L199)

### 6) Tests + verification
- Add/adjust tests to confirm:
  - Recruitment/Procurement tools execute under their own `mcp_tools` roots.
  - Planning still selects correct scope and skill; `plan_json` unchanged.
  - Scenario tests remain green.

If you confirm this plan, I’ll implement in the order above (mcp_tools first so scope execution is real before tightening planning/codegen with BAML), then run the full pytest suite.