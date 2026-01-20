## Current Behavior (What Already Works)
- `execute_skill` plans already support **any scope directory** under `skills_v2/`.
  - The agent infers `skill_group` from the selected skill file path via [_infer_skill_group](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py#L311-L320), so if the skill comes from `Recruitment-scopes/examples/...`, `plan.skill_group` becomes `Recruitment-scopes`.
- Tool docs are already **scope-filtered** during codegen:
  - `WorkflowAgent._docs_registry_for_plan()` reads `plan_json.skill_group` and uses `skills_v2/{skill_group}/tools/mcp_docs/` if it exists, else falls back to the default docs dir ([agent.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py#L234-L246)).

## Gaps (What Needs Changing)
1. **Custom scripts don’t have a scope**, because `_plan_from_dict()` drops `skill_group` unless `action == execute_skill` ([agent.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py#L261-L299)).
   - Result: `custom_script` currently defaults tool docs to HR (`self.default_docs_dir`), so its `tool_contracts` are HR-scoped even if the user request is clearly Recruitment/Procurement.
2. **No explicit “scope registry” / validation contract** to ensure future scopes/tools are added consistently.

## Plan
### 1) Make `skill_group` a first-class concept for *both* skills and custom scripts
- Update `Plan` parsing so `skill_group` can be present for `custom_script` as well:
  - Modify `_plan_from_dict()` to accept `skill_group` when `action in {execute_skill, custom_script}` (instead of only execute_skill).
  - Keep `chat` forcing `skill_group=None`.
- Update planning prompt + schema in [workflow_agent.baml](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/baml_src/workflow_agent.baml) so the planner:
  - Chooses `skill_group` from the discovered scope directories (`HR-scopes`, `Recruitment-scopes`, `Procurement-scopes`, …)
  - For `custom_script`, still sets `skill_group` (the scope that best matches the request).

### 2) Ensure tool docs selection uses `skill_group` for custom scripts
- Keep using `_docs_registry_for_plan()` as the single routing point, but now it will receive `skill_group` for custom scripts too.
- Define fallback behavior explicitly:
  - If planner emits unknown/blank `skill_group`, fall back to `default_docs_dir`.
  - Otherwise use `skills_v2/{skill_group}/tools/mcp_docs/`.

### 3) Add an auto-discovered “scope + tools” validation mechanism
Use **discovery + tests** (no hard-coded scope list) so adding a new scope is just “create folder + tests pass”.
- Add a small helper (either in [skill_registry.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/skill_registry.py) or a new module) that discovers scope dirs as immediate children of `skills_v2/` that end with `-scopes`.
- Add tests that validate for every discovered scope:
  - `tools/mcp_docs/` exists
  - Each MCP directory contains a `server.json`
  - Each `server.json` has a `python_module` (or matches `mcp_tools.<mcp_name>`) that is importable when `tools_pythonpath` points at `agent_workspace/tools`
  - Optionally: tools listed in `server.json.tools` exist as functions.
  - Optionally: if `examples/` exists, at least one `*.md` skill exists.

### 4) Update/extend existing tests to cover non-HR scoping end-to-end
- Extend [test_tool_docs_selection_by_scope.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/tests/test_tool_docs_selection_by_scope.py) or add a new test ensuring:
  - A `custom_script` plan with `skill_group="Recruitment-scopes"` causes codegen to receive Recruitment tool contracts (not HR).

## Expected Result
- `Plan.skill_group` meaningfully supports **HR + Recruitment + Procurement + future scopes**.
- Tool contracts are **scoped** for both `execute_skill` and `custom_script`.
- Adding a new scope becomes:
  - Create `skills_v2/New-scope/tools/mcp_docs/...` + examples
  - Tests enforce structure and importability; no manual updates required.

If you approve, I’ll implement the above changes across:
- [workflow_agent.baml](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/baml_src/workflow_agent.baml)
- [agent.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py)
- Registry/helpers in [skill_registry.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/skill_registry.py) and/or tests
- Tests under `tests/`