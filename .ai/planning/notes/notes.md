# Code Discovery & Implementation Notes: Multi-Turn Workflows

## 1. Execution Signal Extraction
The [PythonCodeExecutor](file:///Users/nguyen.tran/Documents/My Remote Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/code_executor.py) uses `subprocess.run` with `capture_output=True`. This means the agent already has access to the full `stdout`.

**Implementation Note:** 
In `WorkflowExecutor.execute()`, we should add a regex or simple string split to find `CONTINUE_WORKFLOW: <fact>` in `exec_result.stdout`.
- Pattern: `r"CONTINUE_WORKFLOW:\s*(.*)"`
- If multiple facts are emitted, we should collect all of them.

## 2. Planner & BAML Integration
The [Planner](file:///Users/nguyen.tran/Documents/My Remote Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/sub_agents/planner.py) maps the dictionary returned by `baml_bridge.workflow_plan` to a `Plan` object.

**Implementation Note:**
- When updating `baml_src/workflow_agent.baml`, ensure the `requires_lookahead` field is added to both the `Plan` class and the `WorkflowPlan` function return type.
- The `_plan_from_dict` helper in `planner.py` must be updated to read these new fields.

## 3. Session Persistence
The [FileDataLayer](file:///Users/nguyen.tran/Documents/My Remote Vault/mcp-skill-code_exec/agent_workspace/memory/chainlit_data_layer.py) handles the actual YAML reading/writing. [SessionMemory](file:///Users/nguyen.tran/Documents/My Remote Vault/mcp-skill-code_exec/agent_workspace/memory/session_memory.py) provides the high-level API.

**Implementation Note:**
- Instead of just `add_fact`, we might need a dedicated `workflow_state` section in the YAML to track `current_step` and `is_multi_turn`.
- The `FileDataLayer`'s `_load_thread` and `_save_thread` are already robust; we just need to update the dictionary structure they handle.

## 4. Chainlit Loop & HITL
The [chainlit_app_v2.py](file:///Users/nguyen.tran/Documents/My Remote Vault/mcp-skill-code_exec/chainlit_app_v2.py) currently has a `while True` loop for the planning phase but a linear flow for execution.

**Implementation Note:**
- We need to wrap the entire "Plan -> Execute -> Respond" flow in a loop or a state machine to handle the resumption.
- If `requires_lookahead` is true, we should probably auto-execute the first step (discovery) after plan approval, then pause and show the results before the next turn.

## 5. Fact Injection
Currently, `SessionMemory.get_context_summary` injects facts into the prompt.

**Implementation Note:**
- We should ensure that facts discovered in Turn 1 (e.g., "Charlie Davis is a DevOps Engineer") are explicitly passed to `WorkflowCodegen` in Turn 2 so it doesn't try to look them up again.
- Consider adding a `collected_facts` parameter to `WorkflowExecutor.execute()` or `WorkflowCodegen`.
