## Goal
- Revise HR-scope scenario tests so they validate **user intent → chosen skill/steps → generated code → execution logs → response**, and ensure outputs plausibly resolve the user request.
- Introduce a reusable scenario-testing abstraction and an LLM-based qualitative judge (with a deterministic fallback for CI).

## Current State (What the existing test does)
- [test_hr_scopes_scenario_requests.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/tests/test_hr_scopes_scenario_requests.py) currently:
  - Forces plan selection + codegen using a stub LLM (deterministic mapping)
  - Executes code and asserts a stdout substring
  - Does **not** evaluate code quality vs user intent, plan steps quality, or final response quality.

## Design Changes
### 1) Add a Dedicated Scenario Harness (test-only)
- Create `tests/utils/scenario_harness.py` containing:
  - `Scenario` dataclass: `name`, `user_requests`, `expected_skill`, `expected_intent_keywords`, `required_code_patterns`, `required_log_patterns`.
  - `ScenarioRunner`: runs `HRAgent` once per user request and returns a `ScenarioRun` record with `plan_json`, `generated_code`, `exec_stdout/exec_stderr`, `final_response`, and selected skill.
  - Utility to load skill markdown + logic-flow steps (via existing `_extract_logic_flow_steps`) so we can compare planned steps with the skill’s documented flow.

### 2) Add a Qualitative Judge Abstraction
- Create `tests/utils/qualitative_judge.py` with:
  - `JudgeVerdict` dataclass (or typed dict): per-dimension scores and boolean pass/fail.
  - `JudgeLLM` protocol: `chat(messages, temperature) -> str`.
  - `HeuristicJudgeLLM` (default): deterministic rubric that scores:
    - Skill choice matches scenario’s expected skill and request keywords
    - Plan steps overlap with the skill’s `## Logic Flow` steps
    - Generated code contains required imports/calls (regex patterns)
    - Execution logs include required signals (regex patterns)
    - Final response mentions key outcomes (e.g., ticket created, notifications sent)
  - `OpenRouterJudgeLLM` (optional integration): uses [OpenRouterClient](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/hr_agent_v2/openrouter_client.py) to judge qualitatively and return strict JSON. Skips if env vars missing.

### 3) Revise Scenario Tests to Use the Harness + Judge
- Refactor [test_hr_scopes_scenario_requests.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/tests/test_hr_scopes_scenario_requests.py):
  - Replace the monolithic dicts with `Scenario` objects.
  - For each scenario request:
    1. Run the agent with the existing deterministic stub (keeps tests stable)
    2. Assert hard guarantees (plan JSON parseable, execution completed)
    3. Run the judge and assert `verdict.pass == True`
  - Add a second test marked `@pytest.mark.integration` that uses `OpenRouterJudgeLLM` when configured, otherwise `pytest.skip(...)`.

## What Will Be Checked After Revision
- **Code validity**: still enforced by agent compile + successful execution.
- **Execution behavior**: still enforced via log patterns + judge rubric.
- **Response quality**: now checked (at least with deterministic heuristic rubric; optionally via real LLM judge).
- **Intent alignment**: checked across skill name, steps, code patterns, and logs.

## Files to Add / Update
- Add: `tests/utils/scenario_harness.py`
- Add: `tests/utils/qualitative_judge.py`
- Update: `tests/test_hr_scopes_scenario_requests.py` to use harness + judge and add integration-judge test.
- (If needed) Add: `tests/conftest.py` to register `integration` marker cleanly.

## Verification
- Run `python -m pytest -q`.
- Ensure default suite passes without network.
- If `OPENROUTER_API_KEY` + model env vars exist, ensure integration judge test passes; otherwise it is skipped.