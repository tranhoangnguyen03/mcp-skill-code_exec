## Why It’s Failing
- Chainlit is running under your base conda Python, and the runtime `sys.path` does not reliably include the repo root that contains the generated `baml_client/` package.
- `agent_workspace/workflow_agent/baml_bridge.py` imports `baml_client.sync_client`, so any missing repo-root-on-path becomes `ModuleNotFoundError: No module named 'baml_client'`.

## Proposed Fix
- Add a small, early bootstrap to ensure the repo root is on `sys.path` before importing agent modules.
  - Update [chainlit_app_v2.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/chainlit_app_v2.py) to insert `Path(__file__).resolve().parent` into `sys.path` and call `importlib.invalidate_caches()`.
- Strengthen the existing bootstrap in [baml_bridge.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/baml_bridge.py) to:
  - Insert repo root only if absent
  - Call `importlib.invalidate_caches()`
  - Optionally retry the import on first failure inside `workflow_plan` (minimal try/except) so it self-heals if any runtime mutates `sys.path`.

## Verification
- Add a small unit test (or extend the existing Chainlit import test) that simulates “run from outside repo root” by temporarily removing the repo root from `sys.path`, then importing `agent_workspace.workflow_agent.baml_bridge` and confirming `import baml_client` succeeds.
- Run `python -m pytest`.
- (Optional manual) Re-run: `chainlit run chainlit_app_v2.py -w --port 6969` and confirm the error is gone.

## Scope
- Only touches import/bootstrap logic; no changes to BAML generation, tools, or workflow behavior.