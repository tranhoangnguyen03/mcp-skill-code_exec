# Skill-Based Workflow Agent (Chainlit UI)

This UI runs a skill-based automation agent with a human-in-the-loop approval gate.

## Workflow Steps

The agent distinguishes between **working steps** and **response steps**:

| Category | Display | Storage | Examples |
|----------|---------|---------|----------|
| **Working Steps** | `cl.Step()` | `steps[]` array | Plan proposal, generated code, execution output |
| **Response Steps** | `cl.Message()` | `messages[]` array | User inputs, assistant final responses |

## What Happens on Each Message

1. **Plan Phase** (working step): The agent proposes a plan (`chat`, `execute_skill`, or `custom_script`) shown in a Chainlit step
2. **HITL Gate**: The UI pauses and asks you to choose:
   - Approve Plan: proceed to code generation and execution
   - Re-plan: provide feedback and regenerate the plan
   - Cancel Request: stop the workflow
3. **Codegen Phase** (working step): Code generation shown as a Chainlit step
4. **Execute Phase** (working step): Execution output shown as a Chainlit step
5. **Respond Phase** (response step): Final response shown as a message

## Session Memory

Conversation history is stored in YAML files under `agent_workspace/memory/sessions/`:

```yaml
# messages[] stores conversation turns
messages:
  - role: user
    content: Onboard today's new hires
    timestamp: '2024-01-20T10:30:00'
  - role: assistant
    content: Done! 3 employees onboarded.
    timestamp: '2024-01-20T10:31:00'

# steps[] stores working artifacts (plan, code, execution)
steps:
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
```

## Run

```bash
chainlit run chainlit_app_v2.py
```
