# Skill-Based Workflow Agent (Chainlit UI)

This UI runs a skill-based automation agent with a human-in-the-loop approval gate.

## Workflow Steps

The agent distinguishes between **working steps** and **response steps**:

| Category | Display | Storage | Examples |
|----------|---------|---------|----------|
| **Working Steps** | `cl.Step()` | `steps[]` array | Plan proposal, generated code, execution output |
| **Response Steps** | `cl.Message()` | `messages[]` array | User inputs, assistant final responses |

## What Happens on Each Message

1. **Plan Phase** (working step): The agent proposes a plan (`chat`, `execute_skill`, or `custom_script`) shown in a Chainlit step.
2. **HITL Gate**: The UI pauses for human approval. You can:
   - **Approve Plan**: Proceed to code generation and execution.
   - **Re-plan**: Provide feedback to the agent to refine its plan.
   - **Cancel Request**: Terminate the current workflow.
3. **Codegen Phase** (working step): Python code is generated based on the plan and tool documentation.
4. **Execute Phase** (working step): The code is executed, and stdout/stderr are captured.
5. **Respond Phase** (response step): The final summary or chat response is sent as a message.

## Session Memory

Conversation history and working artifacts are persisted as YAML files in `agent_workspace/memory/sessions/`.

### YAML Structure Example

```yaml
messages: # Conversation turns (user/assistant dialogue)
  - role: user
    content: "Onboard today's new hires"
    timestamp: '2024-01-20T10:30:00'
  - role: assistant
    content: "Done! 3 employees onboarded."
    timestamp: '2024-01-20T10:31:00'

steps: # Working artifacts (internal logic)
  - step_type: plan
    category: working
    content: '{"action": "execute_skill", "intent": "Onboard new hires"}'
    metadata: {intent: Onboard new hires, action: execute_skill}
    timestamp: '2024-01-20T10:30:01'
  - step_type: codegen
    category: working
    content: 'def onboard_employees(): ...'
    metadata: {attempt: 1}
    timestamp: '2024-01-20T10:30:15'
  - step_type: execute
    category: working
    content: 'stdout: 3 employees onboarded\nstderr:'
    metadata: {exit_code: 0, attempt: 1}
    timestamp: '2024-01-20T10:31:00'

facts: # Extracted key information
  - fact: "Alice Smith was onboarded today"
    source_turn: 1
    timestamp: '2024-01-20T10:31:05'
```

## Run

```bash
chainlit run chainlit_app_v2.py
```
