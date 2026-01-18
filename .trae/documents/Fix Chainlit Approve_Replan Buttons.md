## Root Cause
- In Chainlit 2.x, `cl.Action` uses a `payload` field (not `value`). The official `AskActionMessage` example expects actions like `cl.Action(name=..., payload={"value": ...}, label=...)` and the response is read via `res["payload"]["value"]`.
- Current code in [chainlit_app_v2.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/chainlit_app_v2.py#L17-L60) builds actions with `value=...` and reads `res.get("value")`, so the UI doesn’t render valid action buttons and the handler can’t proceed.

## Changes
### 1) Fix action construction + response parsing
- Replace `cl.Action(..., value="approve", ...)` with `cl.Action(..., payload={"value": "approve"}, ...)`.
- Update branching to read:
  - `choice = (res or {}).get("payload", {}).get("value")`
  - Compare `choice` to `"approve" | "replan" | "cancel"`.

### 2) Make the gating more robust
- Set `raise_on_timeout=False` and a longer `timeout` (e.g. 3600 seconds) so it doesn’t auto-timeout while a human is reviewing.
- Ensure a clear fallback path if `res is None` (treat as cancel and show a message).

## Verification
- Start Chainlit and send a message (e.g., “let’s onboard the new folks”).
- Confirm the UI shows three buttons: Approve Plan / Re-plan / Cancel Request.
- Click each option:
  - Approve continues to codegen+execute.
  - Re-plan asks for feedback, generates a new plan, and shows buttons again.
  - Cancel stops the run cleanly.
- Add/adjust a small regression test (or manual smoke test) to ensure the approve gate is exercised.
