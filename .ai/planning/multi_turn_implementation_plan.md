# Implementation Plan: Multi-Turn Workflows

This document outlines the step-by-step implementation for enabling multi-turn workflows in the `mcp-skill-code_exec` agent.

## Phase 1: Data Models & State Management

### Task 1.1: Extend BAML Plan Schema
- **File:** `baml_src/workflow_agent.baml`
- **Action:** Add `requires_lookahead` (bool) and `checkpoints` (string array) to the `Plan` class.
- **Verification:** Run `baml build` and ensure `baml_client` updates correctly.

### Task 1.2: Update Python Plan Dataclass
- **File:** `agent_workspace/workflow_agent/sub_agents/planner.py`
- **Action:** Update `Plan` dataclass to include `requires_lookahead: bool = False` and `checkpoints: list[str] = field(default_factory=list)`.
- **Verification:** Ensure `_plan_from_dict` correctly maps the new BAML fields.

### Task 1.3: Create WorkflowState Container
- **File:** `agent_workspace/workflow_agent/types.py`
- **Action:** Add a `WorkflowState` dataclass to track `session_id`, `current_step`, `collected_facts`, and `is_multi_turn`.
- **Verification:** Verify it can be serialized/deserialized for persistence.

### Task 1.4: Extend SessionMemory for State Persistence
- **File:** `agent_workspace/memory/session_memory.py`
- **Action:** Add `save_workflow_state(state: WorkflowState)` and `get_workflow_state() -> WorkflowState | None` methods.
- **Verification:** Check if `thread.yaml` correctly stores the workflow state under a new `workflow_state` key.

---

## Phase 2: Planner Enhancements

### Task 2.1: Update WorkflowPlan Prompt
- **File:** `baml_src/workflow_agent.baml`
- **Action:** Update the `WorkflowPlan` prompt instructions to detect when a request requires external data lookup before final execution (setting `requires_lookahead=True`).
- **Verification:** Test with "Assign Mr.Davis..." and verify `requires_lookahead` is True.

### Task 2.2: Update Planner.plan() logic
- **File:** `agent_workspace/workflow_agent/sub_agents/planner.py`
- **Action:** Ensure the `plan()` method correctly passes through the new multi-turn attributes to the `PlanningResult`.
- **Verification:** Unit test `Planner.plan()` with a mock BAML response.

---

## Phase 3: Executor Continuation Logic

### Task 3.1: Update WorkflowCodegen Prompt
- **File:** `baml_src/workflow_agent.baml`
- **Action:** Update `WorkflowCodegen` to support a "continuation pattern". Instruct the LLM to print `CONTINUE_WORKFLOW: <fact>` when it discovers information needed for the next turn.
- **Verification:** Test code generation for a search task and verify it includes the continuation signal.

### Task 3.2: Detect Continuation Signals in Executor
- **File:** `agent_workspace/workflow_agent/sub_agents/executor.py`
- **Action:** Modify `execute()` to scan `stdout` for `CONTINUE_WORKFLOW:` patterns. Extract facts and update the `ExecuteResult` to include a `needs_continuation` flag.
- **Verification:** Verify that a script printing the signal triggers the flag in `ExecuteResult`.

---

## Phase 4: Agent Orchestration & UI Integration

### Task 4.1: Implement resume_workflow in WorkflowAgent
- **File:** `agent_workspace/workflow_agent/agent.py`
- **Action:** Add `resume_workflow(state: WorkflowState, user_input: str)` method that uses existing facts to bypass initial discovery steps.
- **Verification:** Integration test showing the agent skipping the first step of a 2-step plan.

### Task 4.2: Update Chainlit Message Loop
- **File:** `chainlit_app_v2.py`
- **Action:** Update `@cl.on_message` to check for pending workflow states. If `needs_continuation` is detected after execution, save state and prompt the user (or auto-continue if appropriate).
- **Verification:** End-to-end manual test in the UI.

---

## Phase 5: Verification & Testing

### Task 5.1: Create "Assign Mr.Davis" Integration Test
- **File:** `tests/integration/test_multi_turn_davis.py`
- **Action:** Script a multi-turn conversation where Turn 1 looks up Davis and Turn 2 performs an assignment based on the discovered domain.
- **Verification:** Test passes with 0 exit code and correct final assignment in `candidates.json`.

### Task 5.2: Performance & Regression Testing
- **Action:** Ensure single-turn workflows (e.g., "List all employees") still work without overhead or state corruption.
- **Verification:** All existing tests in `pytest` pass.
