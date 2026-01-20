## What’s Actually Broken (Root Causes)
- **/thread/<id> → 500 despite YAML existing**: the session YAML contains `!!python/object/apply:...StepType` (see [8de6d38d...yaml](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/memory/sessions/8de6d38d-3091-49fc-859d-9dae0e71b75c.yaml#L13-L16)). Our data layer loads threads with `yaml.safe_load()` ([chainlit_data_layer.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/memory/chainlit_data_layer.py)), and SafeLoader cannot parse python object tags → exception → Chainlit returns “Internal Server Error” for `/project/thread/{thread_id}`.
- **Rename/Delete “refresh and create extra conversations”**:
  - The rename/delete endpoints call `is_thread_author(current_user.identifier, thread_id)`.
  - `is_thread_author` compares the returned value from `get_thread_author()` to the user’s identifier (string) ([acl.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/.venv/lib/python3.13/site-packages/chainlit/data/acl.py#L6-L18)).
  - Our `get_thread_author()` incorrectly returns `user_id` (UUID) instead of `user_identifier` ([chainlit_data_layer.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/memory/chainlit_data_layer.py#L229-L233)). So even if YAML loads, author check fails and rename/delete can’t succeed.
  - Additionally, the YAML load crash above can also break author-check (since `get_thread_author` loads the YAML).
- **Compatibility gap**: `BaseDataLayer.update_thread()` does not accept `user_identifier` ([base.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/.venv/lib/python3.13/site-packages/chainlit/data/base.py#L94-L103)). Our current override signature diverges, which is risky even if it “seems to work”.

## Plan (Implementation)
### 1) Stop writing unsafe YAML tags
- Update `SessionMemory.add_working_step()` to serialize `step_type` as a plain string:
  - if `step_type` is an Enum (e.g. `StepType.PLAN`), write `step_type.value`.
- Update `chainlit_app_v2.py` to pass `StepType.PLAN.value` / `.CODEGEN.value` / `.EXECUTE.value` (or rely on the SessionMemory normalization).

### 2) Make thread YAML loading tolerant (fix existing corrupted sessions)
- Implement a custom YAML loader in `FileDataLayer._load_thread()` that:
  - still uses SafeLoader semantics
  - adds a constructor for `tag:yaml.org,2002:python/object/apply:*` that converts the sequence like `- plan` into the scalar string `plan`
- This makes existing sessions (already written with `!!python/object/apply`) load successfully, unblocking `/project/thread/{id}`.

### 3) Fix author identity semantics (rename/delete)
- Change `FileDataLayer.get_thread_author()` to return the **user identifier** (e.g. `testuser`) not the UUID.
  - Use `data["user_identifier"]` if present
  - Else infer it by looking up `_users.yaml` using the stored `user_id`.

### 4) Restore `update_thread` signature compatibility
- Change `FileDataLayer.update_thread()` to match Chainlit’s abstract signature exactly (no extra params).
- Update `chainlit_app_v2.py` to stop passing `user_identifier` into `update_thread` (store `user_id` only; identifier can be inferred from `_users.yaml`).

### 5) Regression tests
- Add tests that:
  - verify `get_thread_author()` returns the identifier (string) for ACL checks
  - verify `_load_thread()` can load legacy `!!python/object/apply` step_type files
  - verify thread rename and delete paths work at the data-layer level (rename changes `name`, delete removes file)

## Expected Outcomes
- `/project/thread/{thread_id}` returns JSON for threads that exist on disk (no more 500).
- Rename and delete actions succeed because author checks compare `identifier` ↔ `identifier`.
- No new YAML files contain python object tags.

If you approve, I’ll implement all changes above and re-run the full test suite, plus a quick manual check of `/project/thread/{id}` for the previously failing thread.