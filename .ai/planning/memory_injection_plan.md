# Plan for Automatic Memory Injection in BAML Agents

Implement automatic injection of the last N conversation turns into all BAML-backed prompts (`plan`, `plan_review`, `codegen`, `chat`, `respond`). This prevents follow-up turns like “tell him…” from losing the referenced entity from the prior turn.

## 1. Memory Format (Past Messages Only)

- The injected memory must include only past messages at the moment the agent runs (no current user message duplicated into the injected history).
- Use a compact plain-text transcript to avoid introducing new structured types into the BAML schema:
  - One line per turn: `User: ...` / `Assistant: ...`
  - Truncate long messages to keep prompts bounded.

## 2. Injection Policy

- Default: inject the last 10 messages.
- Configurable: `agent_memory_max_messages` environment variable (string int).
- Ordering: oldest → newest, with “most recent last” in the prompt.

## 3. Wiring Changes

### 3.1 Chainlit UI entrypoint

- In `chainlit_app_v2.py`, compute `conversation_history` from `SessionMemory` before calling `memory.add_response("user", user_input)`.
- Pass `conversation_history` into all `WorkflowAgent` calls:
  - `agent.plan(...)`
  - `agent.chat(...)` (when action is `chat`)
  - `agent.codegen(...)`
  - `agent.respond(...)`

### 3.2 SessionMemory helper

- Add `SessionMemory.get_conversation_history(max_messages=10) -> str` that returns the transcript string.

### 3.3 WorkflowAgent + bridge + BAML

- Add `conversation_history: string` parameter to BAML functions:
  - `WorkflowPlan`, `WorkflowPlanReview`, `WorkflowCodegen`, `WorkflowChat`, `WorkflowRespond`
- Update `agent_workspace/workflow_agent/baml_bridge.py` wrappers to pass the new parameter.
- Update `agent_workspace/workflow_agent/agent.py` to accept `conversation_history` and forward it everywhere (including retries).
- Run `baml generate` to update `baml_client/`.

## 4. Testing & Validation (High Priority)

### 4.1 Automated tests (must pass in CI)

- Update all monkeypatched BAML fakes in `tests/` to match new signatures.
- Add a regression test that asserts `conversation_history` is passed into:
  - plan, codegen, respond, chat.
- Run the full test suite:
  - `python -m pytest -q`

### 4.2 Manual validation (Chainlit smoke test)

- Run Chainlit, start a new conversation:
  1. “is there a mr.Davis among us?”
  2. “tell him he need to go to internal.example.com/profile/<employee_id> to update his profile.”
- Expectation: the generated code uses Charlie Davis’s ID (103) rather than a placeholder/default employee.

1.  **Multi-turn Context Test (Original Problem)**: This test will replicate the original problem to verify that the fix is effective.
    -   **Turn 1**: Send the message "is there a mr.Davis among us?".
    -   **Turn 2**: Send the message "tell him he need to go to internal.example.com/profile/<employee_id> to update his profile.".
    -   **Assertion**:
        -   Verify that the generated code correctly identifies "Charlie Davis".
        -   Verify that the generated code uses the correct employee ID for Charlie Davis (which is `103` according to `agent_workspace/data/bamboo_hr/employees.json`).
        -   Verify that the final response to the user confirms the action was taken for Charlie Davis.

2.  **Long Conversation History Test**: This test will ensure that the agent can handle a long conversation history without performance degradation or loss of context.
    -   **Setup**: Programmatically create a long conversation history with multiple turns.
    -   **Action**: Ask a question that requires information from the beginning of the conversation.
    -   **Assertion**: Verify that the agent can correctly retrieve and use the information from the early turns.

3.  **User Correction Test**: This test will verify that the agent can handle user corrections in follow-up messages.
    -   **Turn 1**: Send a message with an incorrect detail, e.g., "Onboard our new hire, John Doe".
    -   **Turn 2**: Send a correction, e.g., "Sorry, I meant Jane Doe".
    -   **Assertion**: Verify that the agent uses the corrected information ("Jane Doe") in the subsequent steps.

4.  **Chat History Test**: This test will ensure that the `chat` action correctly uses the conversation history.
    -   **Turn 1**: Ask a question, e.g., "What are the available skills?".
    -   **Turn 2**: Ask a follow-up question, e.g., "Can you tell me more about the first one?".
    -   **Assertion**: Verify that the agent's response in the second turn is relevant to the first skill mentioned in its previous response.
