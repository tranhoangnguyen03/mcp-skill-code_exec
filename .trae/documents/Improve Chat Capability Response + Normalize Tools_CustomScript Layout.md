## Why the current “hey, what can you do?” response is wrong
- The planner correctly selects `action=chat`.
- The chat responder (`WorkflowChat`) is currently a generic assistant prompt, so it ignores repo-specific capabilities.

## Desired behavior
- For capability questions (“what can you do?”), the chat response should summarize:
  - supported scopes/skills from [skills_v2/Readme.md](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/skills_v2/Readme.md)
  - what `custom_script` means + rules from [custom_skill.md](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/custom_skill.md)

## Changes I will implement
### 1) Make the chat agent repo-aware (BAML change)
- Update `WorkflowChat` in `baml_src/workflow_agent.baml` to accept:
  - `skills_readme: string`
  - `custom_skill_md: string`
- Update the prompt so capability questions are answered by summarizing those two inputs (and staying inside the repo’s domain: HR/Recruitment/Procurement workflows + tool-driven custom scripts).
- Update Python bridge `workflow_chat(...)` and `WorkflowAgent.chat(...)` to pass `skills_readme` and the custom script manual.

### 2) Move custom_script manual into skills_v2 (structure cleanup)
- Relocate `agent_workspace/workflow_agent/custom_skill.md` into `agent_workspace/skills_v2/custom_skill.md` (or a similarly named canonical file under `skills_v2/`).
- Update `WorkflowAgent.get_skill_md()` to read from the new path.
- Update the chat change above to read the same canonical file.

### 3) Normalize tool root location (resolve “HR-scopes/tools is special”)
You gave two acceptable options; I’ll implement the “independent folder” option because it avoids duplicating tools into every scope:
- Create a canonical tools root outside `skills_v2`, e.g. `agent_workspace/tools/mcp_tools/`.
- Move the existing `skills_v2/HR-scopes/tools/mcp_tools` package into that canonical location.
- Update `PythonCodeExecutor` initialization and `_tools_root_for_plan()` so every execution uses this canonical tools root (regardless of scope), while scope-specific docs remain under each scope’s `tools/mcp_docs/`.

This keeps `skills_v2` focused on skills/examples/docs, and keeps runnable tool implementations in one place.

### 4) Update docs + tests
- Update repo documentation (Readme snippets if needed) to reflect:
  - canonical tool location
  - canonical custom script manual location
- Update tests that assert tool paths to point at the new canonical `mcp_tools` path.
- Ensure the scenario/judge harness still passes.

### 5) Regenerate BAML client + verify
- Run `baml-cli generate --from ./baml_src`.
- Run `pytest -q`.

## Outcome
- “hey, what can you do?” produces an answer grounded in `skills_v2/Readme.md` + the custom script manual.
- `custom_skill.md` lives under `skills_v2/` as requested.
- `mcp_tools` lives in a single canonical folder independent of `skills_v2` (no per-scope duplication).
