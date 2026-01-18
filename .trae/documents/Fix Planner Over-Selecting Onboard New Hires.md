## Goal
When a user asks for a minimal one-off action (e.g. “just DM new hires a link to update their profile”), the planner should choose `custom_script` instead of over-selecting a heavier prewritten skill like **Onboard New Hires**.

## Approach (Robust, Generalizable)
### 1) Change the planning rubric (BAML prompt tuning, reasoning-based)
Update `WorkflowPlan` in [workflow_agent.baml](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/baml_src/workflow_agent.baml) to remove the blanket “prefer execute_skill” bias and replace it with an explicit decision rubric:
- Choose `execute_skill` only when the user request *requires* the core side effects described by that skill’s manual (not merely “related”).
- If a known skill includes major actions not requested (e.g., ticket creation, calendar events, email), prefer `custom_script`.
- Enforce minimality: do not add additional workflows/tools beyond what the user asked.

This avoids brittle if-keyword rules and instead makes the model validate “does this skill’s described behavior match what the user asked for?” using the provided skills readme/manual context.

### 2) (Optional but recommended) Add a second reasoning check in planning
If the first plan selects `execute_skill`, add a follow-up BAML “review” call (new BAML function) that:
- takes `user_message` + selected `skill_md`
- returns either “keep execute_skill” or “downgrade to custom_script”

This makes the system resilient even if the first classification is biased.

### 3) Regenerate the BAML client
Run `baml-cli generate --from ./baml_src` so the updated prompts (and optional new function) are reflected in `baml_client/`.

## Add Scenario Test (Required)
Add a new scenario test case for:
- Request: “ask the new hires to visit internal.example.com/profile/<employee_id> to update their employee profile”
- Expected behavior:
  - `action == "custom_script"`
  - Code uses `mcp_tools.bamboo_hr` to retrieve today’s hires
  - Code composes the internal URL using `employee["id"]`
  - Code uses `mcp_tools.slack.send_dm` to message each hire
  - Prints a final summary

Implementation-wise, I’ll extend the scenario test harness to support `custom_script` scenarios (expected action + required code/log patterns) without assuming `execute_skill`.

## Verification
- Run `pytest -q`.
- Ensure the new scenario test passes and existing scenarios remain unchanged.
